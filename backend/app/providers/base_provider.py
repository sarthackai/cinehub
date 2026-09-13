from abc import ABC, abstractmethod
from typing import Any


class ContentProvider(ABC):
    """
    Abstract interface for any external content metadata provider.
    Concrete implementations (e.g. TMDBProvider) must implement all of these.
    This keeps the rest of the app decoupled from any single provider's API shape.
    """

    @abstractmethod
    def fetch_trending(self, content_type: str = "movie", time_window: str = "week") -> list[dict[str, Any]]:
        """Return a list of raw trending items from the provider."""
        raise NotImplementedError

    @abstractmethod
    def fetch_new_releases(self, content_type: str = "movie") -> list[dict[str, Any]]:
        """Return a list of raw newly released items from the provider."""
        raise NotImplementedError

    @abstractmethod
    def fetch_upcoming(self, content_type: str = "movie") -> list[dict[str, Any]]:
        """Return a list of raw upcoming items from the provider."""
        raise NotImplementedError

    @abstractmethod
    def fetch_popular(self, content_type: str = "movie") -> list[dict[str, Any]]:
        """Return a list of raw popular items from the provider."""
        raise NotImplementedError

    @abstractmethod
    def fetch_details(self, external_id: str, content_type: str = "movie") -> dict[str, Any]:
        """Return full raw details for a single item, including credits if available."""
        raise NotImplementedError

    @abstractmethod
    def fetch_watch_providers(self, external_id: str, content_type: str = "movie") -> dict[str, Any]:
        """
        Return raw watch-provider (availability) data for a single item, if the
        provider supports it. Callers must treat this as best-effort, not
        authoritative, and always store the source + timestamp alongside it.
        """
        raise NotImplementedError

    @abstractmethod
    def search(self, query: str, content_type: str = "movie") -> list[dict[str, Any]]:
        """Return raw search results matching the query."""
        raise NotImplementedError