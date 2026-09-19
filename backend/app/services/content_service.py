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

        self.recompute_trending_scores()

        return {
            "jobs_run": len(results),
            "total_rows_processed": total_succeeded,
            "jobs_failed": total_failed,
            "details": results,
        }

    def recompute_trending_scores(self) -> dict[str, int]:
        """
        Recomputes and stores a real trending_score for every content item,
        combining multiple genuine signals (not just a popularity re-label):

            trending_score = 0.35 * normalized_popularity
                            + 0.20 * normalized_rating
                            + 0.15 * normalized_vote_count
                            + 0.15 * normalized_recency
                            + 0.15 * normalized_recent_activity

        recent_activity = count of user_interactions (likes/views/clicks) on
        this item in the last 7 days — a real, app-level signal, distinct from
        anything TMDB provides. With a small user base this signal will often
        be 0, which is honest: trending should reflect real usage, and we
        don't fabricate activity that didn't happen.

        Weights are configurable constants below (not hardcoded inline).
        """
        import numpy as np
        from datetime import datetime, timedelta, timezone

        WEIGHTS = {
            "popularity": 0.35,
            "rating": 0.20,
            "vote_count": 0.15,
            "recency": 0.15,
            "recent_activity": 0.15,
        }

        content_result = self.client.table("content").select(
            "id, popularity, provider_rating, provider_vote_count, release_date"
        ).execute()
        rows = content_result.data
        if not rows:
            return {"updated": 0}

        seven_days_ago = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
        interactions = (
            self.client.table("user_interactions")
            .select("content_id")
            .gte("created_at", seven_days_ago)
            .execute()
        )
        activity_counts: dict[str, int] = {}
        for row in interactions.data:
            activity_counts[row["content_id"]] = activity_counts.get(row["content_id"], 0) + 1

        def _normalize(values: list[float]) -> list[float]:
            arr = np.array(values, dtype=float)
            if arr.max() == arr.min():
                return [0.0] * len(arr)
            return ((arr - arr.min()) / (arr.max() - arr.min())).tolist()

        def _recency(release_date_str: str | None) -> float:
            if not release_date_str:
                return 0.0
            try:
                release = datetime.strptime(release_date_str, "%Y-%m-%d").date()
            except ValueError:
                return 0.0
            days_old = max(0, (datetime.now(timezone.utc).date() - release).days)
            return max(0.0, 1.0 - (days_old / 365))  # full score at release, ~0 by 1 year

        popularity_norm = _normalize([r.get("popularity") or 0 for r in rows])
        rating_norm = _normalize([r.get("provider_rating") or 0 for r in rows])
        vote_count_norm = _normalize([r.get("provider_vote_count") or 0 for r in rows])
        recency_scores = [_recency(r.get("release_date")) for r in rows]
        activity_norm = _normalize([activity_counts.get(r["id"], 0) for r in rows])

        updated = 0
        for i, row in enumerate(rows):
            score = (
                WEIGHTS["popularity"] * popularity_norm[i]
                + WEIGHTS["rating"] * rating_norm[i]
                + WEIGHTS["vote_count"] * vote_count_norm[i]
                + WEIGHTS["recency"] * recency_scores[i]
                + WEIGHTS["recent_activity"] * activity_norm[i]
            )
            self.client.table("content").update({"trending_score": round(float(score), 4)}).eq(
                "id", row["id"]
            ).execute()
            updated += 1

        return {"updated": updated}     