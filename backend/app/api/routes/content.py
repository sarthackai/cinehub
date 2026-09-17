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

@router.get("/{content_id}")
def get_content_details(content_id: str):
    from app.database.supabase_client import get_supabase_client

    client = get_supabase_client()

    content_result = client.table("content").select("*").eq("id", content_id).execute()
    if not content_result.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Content not found")
    content = content_result.data[0]

    genre_links = client.table("content_genres").select("genre_id").eq("content_id", content_id).execute()
    genre_ids = [g["genre_id"] for g in genre_links.data]
    genres = []
    if genre_ids:
        genres_result = client.table("genres").select("name").in_("id", genre_ids).execute()
        genres = [g["name"] for g in genres_result.data]

    cast_links = (
        client.table("content_cast")
        .select("person_id, character_name, cast_order")
        .eq("content_id", content_id)
        .order("cast_order")
        .execute()
    )
    cast = []
    for link in cast_links.data:
        person = client.table("people").select("name, profile_image_url").eq("id", link["person_id"]).execute()
        if person.data:
            cast.append(
                {
                    "name": person.data[0]["name"],
                    "character": link.get("character_name"),
                    "profile_image_url": person.data[0].get("profile_image_url"),
                }
            )

    crew_links = client.table("content_crew").select("person_id, role").eq("content_id", content_id).execute()
    crew = []
    for link in crew_links.data:
        person = client.table("people").select("name").eq("id", link["person_id"]).execute()
        if person.data:
            crew.append({"name": person.data[0]["name"], "role": link["role"]})

    return {
        **content,
        "genres": genres,
        "cast": cast,
        "crew": crew,
    }