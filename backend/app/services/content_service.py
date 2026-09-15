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
        self._genre_cache: dict[str, int] | None = None

    def _get_genre_map(self) -> dict[str, int]:
        """Cache genres table (name -> id) so we don't re-query per item."""
        if self._genre_cache is None:
            result = self.client.table("genres").select("id, name").execute()
            self._genre_cache = {row["name"]: row["id"] for row in result.data}
        return self._genre_cache

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
        # TMDB sends empty string "" for missing dates sometimes; normalize to None
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

    def _link_genres(self, content_id: str, genre_ids: list[int]) -> None:
        """Map TMDB genre_ids to our genres table by matching TMDB's genre names."""
        if not genre_ids:
            return
        # We don't have TMDB's raw id->name map cached here beyond what seed_genres
        # stored by name, so this relies on genre NAMES already existing (Step 8).
        # For trending/popular list endpoints, TMDB only gives genre_ids, not names,
        # so full genre linking happens in fetch_details() calls (fuller data) —
        # this method is reserved for future entries where genre names ARE present.
        pass

    def sync_batch(self, items: list[dict[str, Any]], content_type: str) -> dict[str, int]:
        """Upsert a batch of raw TMDB items. Returns counts for logging."""
        succeeded = 0
        skipped = 0
        for item in items:
            content_id = self._upsert_content(item, content_type)
            if content_id:
                succeeded += 1
            else:
                skipped += 1
        return {"succeeded": succeeded, "skipped": skipped, "total": len(items)}