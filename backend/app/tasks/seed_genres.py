"""
One-time (or occasional) script to seed TMDB's genre list into our `genres` table.
Run manually: python -m app.tasks.seed_genres
"""

from app.database.supabase_client import get_supabase_client
from app.providers.tmdb_provider import TMDBProvider


def slugify(name: str) -> str:
    return name.lower().replace(" ", "-").replace("&", "and")


def seed_genres() -> None:
    provider = TMDBProvider()
    client = get_supabase_client()

    movie_genres = provider._get("/genre/movie/list").get("genres", [])
    tv_genres = provider._get("/genre/tv/list").get("genres", [])

    # Merge and dedupe by name (movie/tv genre lists overlap significantly)
    all_genres = {g["name"]: g for g in movie_genres + tv_genres}.values()

    inserted = 0
    for genre in all_genres:
        result = (
            client.table("genres")
            .upsert(
                {"name": genre["name"], "slug": slugify(genre["name"])},
                on_conflict="name",
            )
            .execute()
        )
        inserted += len(result.data or [])

    print(f"Seeded/updated {inserted} genres.")


if __name__ == "__main__":
    seed_genres()