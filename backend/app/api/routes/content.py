from fastapi import APIRouter, HTTPException, status

from app.providers.tmdb_provider import TMDBProvider

router = APIRouter(prefix="/api/content", tags=["content"])


@router.get("/trending")
def get_trending(content_type: str = "movie", time_window: str = "week"):
    provider = TMDBProvider()
    try:
        results = provider.fetch_trending(content_type=content_type, time_window=time_window)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to fetch trending content from metadata provider.",
        )

    # Return a trimmed, frontend-friendly shape for now — full DB storage comes in Step 7.
    simplified = [
        {
            "external_id": item.get("id"),
            "title": item.get("title") or item.get("name"),
            "overview": item.get("overview"),
            "poster_path": item.get("poster_path"),
            "backdrop_path": item.get("backdrop_path"),
            "release_date": item.get("release_date") or item.get("first_air_date"),
            "rating": item.get("vote_average"),
            "vote_count": item.get("vote_count"),
            "popularity": item.get("popularity"),
        }
        for item in results
    ]

    return {"count": len(simplified), "results": simplified}