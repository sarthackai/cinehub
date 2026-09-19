from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.security import require_admin
from app.database.supabase_client import get_supabase_client
from app.services.content_service import ContentSyncService
from app.ml.model_registry import refit_model

router = APIRouter(prefix="/api/admin", tags=["admin"])


class SyncRequest(BaseModel):
    job_name: str
    content_type: str = "movie"
    include_credits: bool = False


@router.post("/sync")
def trigger_sync(payload: SyncRequest, _admin_user: str = Depends(require_admin)):
    service = ContentSyncService()
    result = service.run_sync(
        job_name=payload.job_name,
        content_type=payload.content_type,
        include_credits=payload.include_credits,
    )
    if result["status"] in ("success", "partial") and result["rows_processed"] > 0:
        refit_model()
    return result


@router.post("/sync/full")
def trigger_full_sync(_admin_user: str = Depends(require_admin)):
    """Trigger every sync category for both movies and TV, then refit the model."""
    service = ContentSyncService()
    result = service.run_full_sync()
    if result["total_rows_processed"] > 0:
        refit_model()
    return result


@router.get("/analytics")
def get_admin_analytics(_admin_user: str = Depends(require_admin)):
    """
    System-wide analytics: content/user counts, sync health, popular
    searches, most-favorited content. All computed from real data.
    """
    client = get_supabase_client()

    content_count = client.table("content").select("id", count="exact").execute()
    user_count = client.table("profiles").select("id", count="exact").execute()
    movie_count = (
        client.table("content").select("id", count="exact").eq("content_type", "movie").execute()
    )
    tv_count = client.table("content").select("id", count="exact").eq("content_type", "tv").execute()

    recent_syncs = (
        client.table("sync_logs")
        .select("job_name, provider, status, rows_processed, error_message, started_at, finished_at")
        .order("started_at", desc=True)
        .limit(20)
        .execute()
    )

    search_history = client.table("search_history").select("query").execute()
    search_counts: dict[str, int] = {}
    for row in search_history.data:
        q = row["query"].strip().lower()
        if q:
            search_counts[q] = search_counts.get(q, 0) + 1
    popular_searches = sorted(search_counts.items(), key=lambda x: x[1], reverse=True)[:10]

    favorites = client.table("favorites").select("content_id").execute()
    favorite_counts: dict[str, int] = {}
    for row in favorites.data:
        favorite_counts[row["content_id"]] = favorite_counts.get(row["content_id"], 0) + 1
    top_favorited_ids = sorted(favorite_counts.items(), key=lambda x: x[1], reverse=True)[:10]

    most_favorited = []
    if top_favorited_ids:
        ids = [cid for cid, _ in top_favorited_ids]
        content_rows = client.table("content").select("id, title, poster_url").in_("id", ids).execute()
        title_by_id = {row["id"]: row for row in content_rows.data}
        for cid, count in top_favorited_ids:
            if cid in title_by_id:
                most_favorited.append(
                    {
                        "content_id": cid,
                        "title": title_by_id[cid]["title"],
                        "poster_url": title_by_id[cid].get("poster_url"),
                        "favorite_count": count,
                    }
                )

    return {
        "totals": {
            "content": content_count.count,
            "movies": movie_count.count,
            "tv_shows": tv_count.count,
            "users": user_count.count,
        },
        "recent_syncs": recent_syncs.data,
        "popular_searches": [{"query": q, "count": c} for q, c in popular_searches],
        "most_favorited": most_favorited,
    }