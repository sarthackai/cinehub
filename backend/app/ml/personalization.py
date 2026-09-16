"""
Builds a per-user preference profile from their real interaction signals
(ratings, watch history, favorites) and uses it to score unseen content
against the content-based and semantic models.

Design notes:
- We build the profile as a weighted average of the CONTENT VECTORS (TF-IDF
  or embedding space) of items the user has positively engaged with, not as
  a separate hand-crafted feature vector. This means "preference similarity"
  can be computed with the same cosine_similarity machinery as item-to-item
  similarity, keeping the two models consistent.
- Signal weighting (deliberately simple and documented, not hidden):
    rating 5.0        -> weight 1.0
    rating 4.0         -> weight 0.7
    rating <= 3.0      -> weight 0.3 (still some signal, they finished it)
    favorited           -> +0.5 additional weight
    watched >80% progress -> +0.3 additional weight
  These are configurable constants below, not magic numbers buried in logic.
"""

import logging

import numpy as np

from app.database.supabase_client import get_supabase_client

logger = logging.getLogger("streamsync")

RATING_WEIGHTS = {5.0: 1.0, 4.5: 0.85, 4.0: 0.7, 3.5: 0.5, 3.0: 0.3}
DEFAULT_RATING_WEIGHT = 0.2
FAVORITE_BONUS = 0.5
WATCHED_BONUS = 0.3
WATCHED_THRESHOLD = 80.0


def _rating_weight(rating: float | None) -> float:
    if rating is None:
        return 0.0
    # Find the closest defined rating tier at or below the given rating
    applicable = [w for r, w in RATING_WEIGHTS.items() if rating >= r]
    return max(applicable) if applicable else DEFAULT_RATING_WEIGHT


def get_user_signal_weights(user_id: str) -> dict[str, float]:
    """
    Returns {content_id: weight} for every item the user has engaged with,
    combining rating, favorite, and watch-progress signals.
    """
    client = get_supabase_client()
    weights: dict[str, float] = {}

    ratings = client.table("ratings").select("content_id, rating").eq("user_id", user_id).execute()
    for row in ratings.data:
        weights[row["content_id"]] = weights.get(row["content_id"], 0.0) + _rating_weight(row["rating"])

    favorites = client.table("favorites").select("content_id").eq("user_id", user_id).execute()
    for row in favorites.data:
        weights[row["content_id"]] = weights.get(row["content_id"], 0.0) + FAVORITE_BONUS

    watch_history = client.table("watch_history").select("content_id, progress_percent").eq(
        "user_id", user_id
    ).execute()
    for row in watch_history.data:
        if (row.get("progress_percent") or 0) >= WATCHED_THRESHOLD:
            weights[row["content_id"]] = weights.get(row["content_id"], 0.0) + WATCHED_BONUS

    return weights


def build_preference_vector(
    user_id: str, content_id_to_index: dict[str, int], item_vectors: np.ndarray
) -> np.ndarray | None:
    """
    Builds a single weighted-average vector representing the user's taste,
    in the same vector space as item_vectors (TF-IDF matrix or embeddings).
    Returns None if the user has no usable signal yet (cold start).
    """
    signal_weights = get_user_signal_weights(user_id)
    if not signal_weights:
        logger.info("No preference signal for user %s — cold start.", user_id)
        return None

    weighted_vectors = []
    total_weight = 0.0
    for content_id, weight in signal_weights.items():
        idx = content_id_to_index.get(content_id)
        if idx is None:
            continue  # item not in current fitted model (e.g. removed/unsynced)
        weighted_vectors.append(item_vectors[idx] * weight)
        total_weight += weight

    if not weighted_vectors or total_weight == 0:
        return None

    stacked = np.vstack(weighted_vectors) if hasattr(weighted_vectors[0], "shape") else np.array(weighted_vectors)
    preference_vector = np.sum(stacked, axis=0) / total_weight
    return preference_vector