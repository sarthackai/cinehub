import logging
from typing import Any

import httpx

from app.core.config import settings
from app.providers.base_provider import ContentProvider

logger = logging.getLogger("streamsync")

TMDB_BASE_URL = "https://api.themoviedb.org/3"


class TMDBProvider(ContentProvider):
    """
    Concrete ContentProvider implementation backed by TMDB (The Movie Database).

    Notes on limitations (documented deliberately, not hidden):
    - TMDB's `watch/providers` data is community-sourced and NOT contractually
      guaranteed to be accurate per region. We surface it as-is, always tagged
      with source="tmdb" and a timestamp, and never claim it as definitive.
    - Free-tier TMDB has generous but non-infinite rate limits; we keep timeouts
      short and let calling code (sync_tasks.py) handle retries/backoff.
    """

    def __init__(self) -> None:
        self._client = httpx.Client(
            base_url=TMDB_BASE_URL,
            headers={
                "Authorization": f"Bearer {settings.CONTENT_METADATA_API_KEY}",
                "accept": "application/json",
            },
            timeout=10.0,
        )

    def _get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        try:
            response = self._client.get(path, params=params or {})
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as exc:
            logger.error("TMDB API error on %s: %s", path, exc.response.text)
            raise
        except httpx.RequestError as exc:
            logger.error("TMDB request failed on %s: %s", path, str(exc))
            raise

    def fetch_trending(self, content_type: str = "movie", time_window: str = "week") -> list[dict[str, Any]]:
        data = self._get(f"/trending/{content_type}/{time_window}")
        return data.get("results", [])

    def fetch_new_releases(self, content_type: str = "movie") -> list[dict[str, Any]]:
        endpoint = "now_playing" if content_type == "movie" else "on_the_air"
        data = self._get(f"/{content_type}/{endpoint}")
        return data.get("results", [])

    def fetch_upcoming(self, content_type: str = "movie") -> list[dict[str, Any]]:
        if content_type != "movie":
            # TMDB doesn't have a dedicated "upcoming" endpoint for TV;
            # airing_today is the closest equivalent.
            data = self._get("/tv/airing_today")
            return data.get("results", [])
        data = self._get("/movie/upcoming")
        return data.get("results", [])

    def fetch_popular(self, content_type: str = "movie") -> list[dict[str, Any]]:
        data = self._get(f"/{content_type}/popular")
        return data.get("results", [])

    def fetch_details(self, external_id: str, content_type: str = "movie") -> dict[str, Any]:
        return self._get(
            f"/{content_type}/{external_id}",
            params={"append_to_response": "credits"},
        )

    def fetch_watch_providers(self, external_id: str, content_type: str = "movie") -> dict[str, Any]:
        return self._get(f"/{content_type}/{external_id}/watch/providers")

    def search(self, query: str, content_type: str = "movie") -> list[dict[str, Any]]:
        data = self._get(f"/search/{content_type}", params={"query": query})
        return data.get("results", [])