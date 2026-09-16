"""
Transforms raw TMDB payloads into our internal schema and upserts them into
Supabase. Handles genre mapping, cast/crew people records, and deduplication
via the (external_id, provider) unique constraint on `content`.
"""

import logging
from typing import Any

from app.database.supabase_client import get_supabase_client
from app.providers.tmdb_provider import TMDBProvider

logger = logging.getLogger("streamsync")

TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p/w780"
TMDB_BACKDROP_BASE = "https://image.tmdb.org/t/p/w1280"
TMDB_PROFILE_BASE = "https://image.tmdb.org/t/p/w185"

MAX_CAST_MEMBERS = 10  # keep top-billed cast only, avoid bloating the DB
CREW_ROLES_TO_KEEP = {"Director", "Creator", "Writer"}


def _poster_url(path: str | None) -> str | None:
    return f"{TMDB_IMAGE_BASE}{path}" if path else None


def _backdrop_url(path: str | None) -> str | None:
    return f"{TMDB_BACKDROP_BASE}{path}" if path else None


def _profile_url(path: str | None) -> str | None:
    return f"{TMDB_PROFILE_BASE}{path}" if path else None


class ContentSyncService:
    def __init__(self, max_retries: int = 3) -> None:
        self.provider = TMDBProvider(max_retries=max_retries)
        self.client = get_supabase_client()
        self._our_genre_cache: dict[str, int] | None = None
        self._tmdb_genre_id_to_name: dict[int, str] | None = None

    def _get_our_genre_map(self) -> dict[str, int]:
        if self._our_genre_cache is None:
            result = self.client.table("genres").select("id, name").execute()
            self._our_genre_cache = {row["name"]: row["id"] for row in result.data}
        return self._our_genre_cache

    def _get_tmdb_genre_id_map(self) -> dict[int, str]:
        if self._tmdb_genre_id_to_name is None:
            movie_genres = self.provider._get("/genre/movie/list").get("genres", [])
            tv_genres = self.provider._get("/genre/tv/list").get("genres", [])
            merged: dict[int, str] = {}
            for g in movie_genres + tv_genres:
                merged[g["id"]] = g["name"]
            self._tmdb_genre_id_to_name = merged
        return self._tmdb_genre_id_to_name

    def _upsert_content(self, item: dict[str, Any], content_type: str) -> str | None:
        title = item.get("title") or item.get("name")
        if not title or not item.get("id"):
            logger.warning("Skipping item with missing title/id: %s", item)
            return None

        row = {
            "external_id": str(item["id"]),
            "provider": "tmdb",
            "content_type": content_type,
            "title": title,
            "original_title": item.get("original_title") or item.get("original_name"),
            "overview": item.get("overview"),
            "poster_url": _poster_url(item.get("poster_path")),
            "backdrop_url": _backdrop_url(item.get("backdrop_path")),
            "release_date": (item.get("release_date") or item.get("first_air_date")) or None,
            "language": item.get("original_language"),
            "provider_rating": item.get("vote_average"),
            "provider_vote_count": item.get("vote_count"),
            "popularity": item.get("popularity"),
        }
        if row["release_date"] == "":
            row["release_date"] = None

        result = (
            self.client.table("content")
            .upsert(row, on_conflict="external_id,provider")
            .execute()
        )
        if not result.data:
            return None
        return result.data[0]["id"]

    def _link_genres(self, content_id: str, tmdb_genre_ids: list[int]) -> None:
        if not tmdb_genre_ids:
            return

        tmdb_id_to_name = self._get_tmdb_genre_id_map()
        our_name_to_id = self._get_our_genre_map()

        rows_to_insert = []
        for tmdb_gid in tmdb_genre_ids:
            genre_name = tmdb_id_to_name.get(tmdb_gid)
            if not genre_name:
                continue
            our_genre_id = our_name_to_id.get(genre_name)
            if not our_genre_id:
                logger.warning("Genre '%s' not found in our genres table — run seed_genres.py", genre_name)
                continue
            rows_to_insert.append({"content_id": content_id, "genre_id": our_genre_id})

        if rows_to_insert:
            self.client.table("content_genres").upsert(
                rows_to_insert, on_conflict="content_id,genre_id"
            ).execute()

    def _upsert_person(self, tmdb_person_id: int, name: str, profile_path: str | None) -> str | None:
        """Upsert a person (cast or crew member) and return our internal people.id."""
        row = {
            "external_id": str(tmdb_person_id),
            "provider": "tmdb",
            "name": name,
            "profile_image_url": _profile_url(profile_path),
        }
        result = (
            self.client.table("people")
            .upsert(row, on_conflict="external_id,provider")
            .execute()
        )
        if not result.data:
            return None
        return result.data[0]["id"]

    def _link_cast_and_crew(self, content_id: str, external_id: str, content_type: str) -> None:
        """Fetch full details (with credits) for one item and link cast/crew."""
        details = self.provider.fetch_details(external_id, content_type)
        credits = details.get("credits", {})

        cast_list = credits.get("cast", [])[:MAX_CAST_MEMBERS]
        cast_rows = []
        for member in cast_list:
            person_id = self._upsert_person(member["id"], member["name"], member.get("profile_path"))
            if person_id:
                cast_rows.append(
                    {
                        "content_id": content_id,
                        "person_id": person_id,
                        "character_name": member.get("character"),
                        "cast_order": member.get("order"),
                    }
                )
        if cast_rows:
            self.client.table("content_cast").upsert(
                cast_rows, on_conflict="content_id,person_id,character_name"
            ).execute()

        crew_list = [c for c in credits.get("crew", []) if c.get("job") in CREW_ROLES_TO_KEEP]
        crew_rows = []
        for member in crew_list:
            person_id = self._upsert_person(member["id"], member["name"], member.get("profile_path"))
            if person_id:
                crew_rows.append(
                    {
                        "content_id": content_id,
                        "person_id": person_id,
                        "role": member["job"],
                    }
                )
        if crew_rows:
            self.client.table("content_crew").upsert(
                crew_rows, on_conflict="content_id,person_id,role"
            ).execute()

    def sync_batch(
        self, items: list[dict[str, Any]], content_type: str, include_credits: bool = False
    ) -> dict[str, int]:
        """Upsert a batch of raw TMDB items, including genre links and optionally
        cast/crew (which costs one extra API call per item)."""
        succeeded = 0
        skipped = 0
        for item in items:
            content_id = self._upsert_content(item, content_type)
            if content_id:
                self._link_genres(content_id, item.get("genre_ids", []))
                if include_credits:
                    try:
                        self._link_cast_and_crew(content_id, str(item["id"]), content_type)
                    except Exception:
                        logger.exception("Failed to sync credits for content_id=%s", content_id)
                succeeded += 1
            else:
                skipped += 1
        return {"succeeded": succeeded, "skipped": skipped, "total": len(items)}

    def run_sync(
        self,
        job_name: str,
        content_type: str = "movie",
        include_credits: bool = False,
    ) -> dict[str, Any]:
        """
        Run a named sync job (e.g. 'trending', 'popular', 'new_releases',
        'upcoming'), fetch from TMDB, sync to DB, and record the outcome in
        sync_logs regardless of success or failure.
        """
        from datetime import datetime, timezone

        started_at = datetime.now(timezone.utc).isoformat()
        status = "success"
        error_message = None
        rows_processed = 0

        try:
            fetch_map = {
                "trending": self.provider.fetch_trending,
                "popular": self.provider.fetch_popular,
                "new_releases": self.provider.fetch_new_releases,
                "upcoming": self.provider.fetch_upcoming,
            }
            fetch_fn = fetch_map.get(job_name)
            if fetch_fn is None:
                raise ValueError(f"Unknown job_name: {job_name}")

            items = fetch_fn(content_type)
            result = self.sync_batch(items, content_type, include_credits=include_credits)
            rows_processed = result["succeeded"]
            if result["skipped"] > 0:
                status = "partial"

        except Exception as exc:
            status = "failed"
            error_message = str(exc)
            logger.exception("Sync job '%s' failed", job_name)

        finished_at = datetime.now(timezone.utc).isoformat()

        self.client.table("sync_logs").insert(
            {
                "job_name": job_name,
                "provider": "tmdb",
                "status": status,
                "rows_processed": rows_processed,
                "error_message": error_message,
                "started_at": started_at,
                "finished_at": finished_at,
            }
        ).execute()

        return {
            "job_name": job_name,
            "status": status,
            "rows_processed": rows_processed,
            "error_message": error_message,
        }

    def run_full_sync(self, include_credits: bool = False) -> dict[str, Any]:
        """
        Run every sync job (trending, popular, new_releases, upcoming) for
        both movies and TV shows. Returns a summary of all runs. Each
        individual job is still logged separately in sync_logs.
        """
        job_names = ["trending", "popular", "new_releases", "upcoming"]
        content_types = ["movie", "tv"]

        results = []
        for content_type in content_types:
            for job_name in job_names:
                result = self.run_sync(job_name, content_type, include_credits=include_credits)
                results.append({**result, "content_type": content_type})

        total_succeeded = sum(r["rows_processed"] for r in results)
        total_failed = sum(1 for r in results if r["status"] == "failed")

        return {
            "jobs_run": len(results),
            "total_rows_processed": total_succeeded,
            "jobs_failed": total_failed,
            "details": results,
     }       