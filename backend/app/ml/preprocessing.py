"""
Loads content from Supabase and builds a cleaned, combined text representation
per item — the "soup" of title + genres + overview + cast + director + language
that Phase 8 (TF-IDF) and Phase 9 (embeddings) will both vectorize.

Design notes:
- We fetch cast/crew separately and join in Python rather than relying on
  Supabase's nested embed syntax for every join, to keep queries simple and
  debuggable, and because content_cast is capped at ~10 rows/item (Phase 5),
  so this stays cheap even at a few thousand titles.
- Missing values are handled explicitly (empty string, not None) so string
  concatenation never crashes on NoneType.
"""

import logging
import re

import pandas as pd

from app.database.supabase_client import get_supabase_client

logger = logging.getLogger("streamsync")

MAX_CAST_IN_SOUP = 5  # top-billed cast only, to keep the text soup focused


def _clean_text(text: str | None) -> str:
    """Lowercase, strip punctuation/extra whitespace. Returns '' for None."""
    if not text:
        return ""
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _fetch_content_dataframe() -> pd.DataFrame:
    client = get_supabase_client()

    content_result = client.table("content").select(
        "id, external_id, content_type, title, overview, language, "
        "release_date, provider_rating, provider_vote_count, popularity, poster_url, trending_score"
    ).execute()
    content_df = pd.DataFrame(content_result.data)

    if content_df.empty:
        logger.warning("No content found in database — run a sync first.")
        return content_df

    # Genres: content_genres -> genres, joined and grouped into a list per content_id
    genre_links = client.table("content_genres").select("content_id, genre_id").execute()
    genres = client.table("genres").select("id, name").execute()
    genre_name_by_id = {g["id"]: g["name"] for g in genres.data}

    genre_map: dict[str, list[str]] = {}
    for link in genre_links.data:
        name = genre_name_by_id.get(link["genre_id"])
        if name:
            genre_map.setdefault(link["content_id"], []).append(name)

    # Cast: content_cast -> people, top N per content_id, ordered by cast_order
    cast_links = client.table("content_cast").select(
        "content_id, person_id, cast_order"
    ).order("cast_order").execute()
    people = client.table("people").select("id, name").execute()
    person_name_by_id = {p["id"]: p["name"] for p in people.data}

    cast_map: dict[str, list[str]] = {}
    for link in cast_links.data:
        name = person_name_by_id.get(link["person_id"])
        if name and len(cast_map.get(link["content_id"], [])) < MAX_CAST_IN_SOUP:
            cast_map.setdefault(link["content_id"], []).append(name)

    # Crew: content_crew -> people, filter to Director role for the soup
    crew_links = client.table("content_crew").select(
        "content_id, person_id, role"
    ).execute()
    director_map: dict[str, list[str]] = {}
    for link in crew_links.data:
        if link["role"] == "Director":
            name = person_name_by_id.get(link["person_id"])
            if name:
                director_map.setdefault(link["content_id"], []).append(name)

    content_df["genres"] = content_df["id"].map(lambda cid: genre_map.get(cid, []))
    content_df["cast"] = content_df["id"].map(lambda cid: cast_map.get(cid, []))
    content_df["directors"] = content_df["id"].map(lambda cid: director_map.get(cid, []))

    return content_df


def build_content_soup(df: pd.DataFrame) -> pd.DataFrame:
    """
    Adds a 'soup' column: cleaned, combined text per item, ready for TF-IDF or
    embedding. Also drops rows with no usable text at all (title AND overview
    both missing — extremely rare but possible with bad provider data).
    """
    df = df.copy()

    # Handle missing values explicitly
    df["title"] = df["title"].fillna("")
    df["overview"] = df["overview"].fillna("")
    df["language"] = df["language"].fillna("")

    # Deduplicate on (external_id would be the true key, but 'id' is already
    # our deduped primary key from the upsert logic in Phase 5 — this is a
    # defensive extra check in case of any data anomaly)
    before = len(df)
    df = df.drop_duplicates(subset=["id"])
    after = len(df)
    if before != after:
        logger.warning("Dropped %d duplicate content rows during preprocessing.", before - after)

    def make_soup(row) -> str:
        parts = [
            _clean_text(row["title"]),
            _clean_text(row["title"]),  # weighted x2: title matters most for similarity
            " ".join(_clean_text(g) for g in row["genres"]),
            _clean_text(row["overview"]),
            " ".join(_clean_text(c) for c in row["cast"]),
            " ".join(_clean_text(d) for d in row["directors"]),
            _clean_text(row["language"]),
        ]
        return " ".join(p for p in parts if p)

    df["soup"] = df.apply(make_soup, axis=1)

    # Drop rows with an empty soup (no usable text at all)
    before = len(df)
    df = df[df["soup"].str.strip() != ""]
    after = len(df)
    if before != after:
        logger.warning("Dropped %d content rows with no usable text.", before - after)

    return df.reset_index(drop=True)


def load_and_preprocess_content() -> pd.DataFrame:
    """Main entry point: fetch from Supabase, clean, and return the soup-enriched DataFrame."""
    df = _fetch_content_dataframe()
    if df.empty:
        return df
    return build_content_soup(df)