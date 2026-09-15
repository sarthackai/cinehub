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


def _poster_url(path: str | None) -> str | None:
    return f"{TMDB_IMAGE_BASE}{path}" if path else None


def _backdrop_url(path: str | None) -> str | None:
    return f"{TMDB_BACKDROP_BASE}{path}" if path else None


class ContentSyncService:
    def __init__(self) -> None:
        self.provider = TMDBProvider()
        self.client = get_supabase_client()
        self._our_genre_cache: dict[str, int] | None = None
        self._tmdb_genre_id_to_name: dict[int, str] | None = None

    def _get_our_genre_map(self) -> dict[str, int]:
        """Our internal genres table: name -> our genres.id"""
        if self._our_genre_cache is None:
            result = self.client.table("genres").select("id, name").execute()
            self._our_genre_cache = {row["name"]: row["id"] for row in result.data}
        return self._our_genre_cache

    def _get_tmdb_genre_id_map(self) -> dict[int, str]:
        """TMDB's own genre id -> name map (movie + tv combined)."""
        if self._tmdb_genre_id_to_name is None:
            movie_genres = self.provider._get("/genre/movie/list").get("genres", [])
            tv_genres = self.provider._get("/genre/tv/list").get("genres", [])
            merged: dict[int, str] = {}
            for g in movie_genres + tv_genres:
                merged[g["id"]] = g["name"]
            self._tmdb_genre_id_to_name = merged
        return self._tmdb_genre_id_to_name

    def _upsert_content(self, item: dict[str, Any], content_type: str) -> str | None:
        """Upsert a single raw TMDB item into `content`. Returns the content id."""
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
        """Translate TMDB genre_ids -> our genre names -> our genres.id, then upsert
        the (content_id, genre_id) rows into content_genres."""
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

    def sync_batch(self, items: list[dict[str, Any]], content_type: str) -> dict[str, int]:
        """Upsert a batch of raw TMDB items, including genre links. Returns counts."""
        succeeded = 0
        skipped = 0
        for item in items:
            content_id = self._upsert_content(item, content_type)
            if content_id:
                self._link_genres(content_id, item.get("genre_ids", []))
                succeeded += 1
            else:
                skipped += 1
        return {"succeeded": succeeded, "skipped": skipped, "total": len(items)}
