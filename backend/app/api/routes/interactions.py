from fastapi import APIRouter, Depends, HTTPException, status

from app.core.security import get_current_user_id
from app.database.supabase_client import get_supabase_client
from app.schemas.interactions import ContentIdRequest, RatingRequest, WatchProgressRequest

router = APIRouter(prefix="/api", tags=["interactions"])


# --- Favorites ---

@router.post("/favorites")
def add_favorite(payload: ContentIdRequest, user_id: str = Depends(get_current_user_id)):
    client = get_supabase_client()
    client.table("favorites").upsert(
        {"user_id": user_id, "content_id": payload.content_id}
    ).execute()
    return {"status": "added"}


@router.delete("/favorites/{content_id}")
def remove_favorite(content_id: str, user_id: str = Depends(get_current_user_id)):
    client = get_supabase_client()
    client.table("favorites").delete().eq("user_id", user_id).eq("content_id", content_id).execute()
    return {"status": "removed"}


@router.get("/favorites")
def list_favorites(user_id: str = Depends(get_current_user_id)):
    client = get_supabase_client()
    links = client.table("favorites").select("content_id, created_at").eq("user_id", user_id).execute()
    if not links.data:
        return {"count": 0, "results": []}

    content_ids = [row["content_id"] for row in links.data]
    content = (
        client.table("content")
        .select("id, title, poster_url, release_date, provider_rating")
        .in_("id", content_ids)
        .execute()
    )
    results = [
        {
            "content_id": row["id"],
            "title": row["title"],
            "poster_url": row.get("poster_url"),
            "release_date": row.get("release_date"),
            "rating": row.get("provider_rating"),
        }
        for row in content.data
    ]
    return {"count": len(results), "results": results}


# --- Watchlist ---

@router.post("/watchlist")
def add_to_watchlist(payload: ContentIdRequest, user_id: str = Depends(get_current_user_id)):
    client = get_supabase_client()
    client.table("watchlist").upsert(
        {"user_id": user_id, "content_id": payload.content_id}
    ).execute()
    return {"status": "added"}


@router.delete("/watchlist/{content_id}")
def remove_from_watchlist(content_id: str, user_id: str = Depends(get_current_user_id)):
    client = get_supabase_client()
    client.table("watchlist").delete().eq("user_id", user_id).eq("content_id", content_id).execute()
    return {"status": "removed"}


@router.get("/watchlist")
def list_watchlist(user_id: str = Depends(get_current_user_id)):
    client = get_supabase_client()
    links = client.table("watchlist").select("content_id, created_at").eq("user_id", user_id).execute()
    if not links.data:
        return {"count": 0, "results": []}

    content_ids = [row["content_id"] for row in links.data]
    content = (
        client.table("content")
        .select("id, title, poster_url, release_date, provider_rating")
        .in_("id", content_ids)
        .execute()
    )
    results = [
        {
            "content_id": row["id"],
            "title": row["title"],
            "poster_url": row.get("poster_url"),
            "release_date": row.get("release_date"),
            "rating": row.get("provider_rating"),
        }
        for row in content.data
    ]
    return {"count": len(results), "results": results}


# --- Ratings ---

@router.post("/ratings")
def rate_content(payload: RatingRequest, user_id: str = Depends(get_current_user_id)):
    if not (0.5 <= payload.rating <= 5.0):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Rating must be between 0.5 and 5.0",
        )
    client = get_supabase_client()
    client.table("ratings").upsert(
        {"user_id": user_id, "content_id": payload.content_id, "rating": payload.rating}
    ).execute()
    return {"status": "rated", "rating": payload.rating}


@router.get("/ratings")
def list_ratings(user_id: str = Depends(get_current_user_id)):
    client = get_supabase_client()
    ratings = client.table("ratings").select("content_id, rating").eq("user_id", user_id).execute()
    return {"count": len(ratings.data), "results": ratings.data}


# --- Watch history ---

@router.post("/watch-history")
def record_watch(payload: WatchProgressRequest, user_id: str = Depends(get_current_user_id)):
    client = get_supabase_client()
    client.table("watch_history").insert(
        {
            "user_id": user_id,
            "content_id": payload.content_id,
            "progress_percent": payload.progress_percent,
        }
    ).execute()
    return {"status": "recorded"}