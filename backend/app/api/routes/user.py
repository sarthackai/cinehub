from collections import Counter

from fastapi import APIRouter, Depends

from app.core.security import get_current_user_id
from app.database.supabase_client import get_supabase_client

router = APIRouter(prefix="/api/user", tags=["user"])


@router.get("/dashboard")
def get_dashboard(user_id: str = Depends(get_current_user_id)):
    """
    Aggregated analytics for the logged-in user: totals, favorite genres,
    ratings distribution, watch history count. All computed from real
    interaction data — no fabricated metrics.
    """
    client = get_supabase_client()

    watch_history = client.table("watch_history").select("content_id").eq("user_id", user_id).execute()
    ratings = client.table("ratings").select("content_id, rating").eq("user_id", user_id).execute()
    favorites = client.table("favorites").select("content_id").eq("user_id", user_id).execute()
    watchlist = client.table("watchlist").select("content_id").eq("user_id", user_id).execute()
    search_history = client.table("search_history").select("query").eq("user_id", user_id).execute()

    # Genre breakdown: pull genres for every item the user has interacted with
    # (watched, rated, or favorited), deduplicated by content_id.
    interacted_content_ids = set()
    for row in watch_history.data:
        interacted_content_ids.add(row["content_id"])
    for row in ratings.data:
        interacted_content_ids.add(row["content_id"])
    for row in favorites.data:
        interacted_content_ids.add(row["content_id"])

    genre_counter: Counter[str] = Counter()
    if interacted_content_ids:
        genre_links = (
            client.table("content_genres")
            .select("content_id, genre_id")
            .in_("content_id", list(interacted_content_ids))
            .execute()
        )
        genre_ids = list({row["genre_id"] for row in genre_links.data})
        if genre_ids:
            genres = client.table("genres").select("id, name").in_("id", genre_ids).execute()
            genre_name_by_id = {g["id"]: g["name"] for g in genres.data}
            for link in genre_links.data:
                name = genre_name_by_id.get(link["genre_id"])
                if name:
                    genre_counter[name] += 1

    rating_values = [r["rating"] for r in ratings.data]
    avg_rating_given = round(sum(rating_values) / len(rating_values), 2) if rating_values else None

    return {
        "totals": {
            "watched": len(watch_history.data),
            "rated": len(ratings.data),
            "favorites": len(favorites.data),
            "watchlist": len(watchlist.data),
            "searches": len(search_history.data),
        },
        "favorite_genres": [
            {"genre": genre, "count": count} for genre, count in genre_counter.most_common(8)
        ],
        "average_rating_given": avg_rating_given,
    }