"""
Hybrid recommendation engine — combines content-based, semantic, personalized,
rating, popularity, trending, and recency signals into one final ranked list,
with a human-readable explanation per recommendation.

Final Score = w1*content_sim + w2*semantic_sim + w3*user_pref
            + w4*rating_score + w5*popularity_score
            + w6*trending_score + w7*recency_score

Weights are configurable constants below (not hardcoded inline), per the
original spec. All scores are normalized to [0, 1] before weighting so no
single signal dominates purely due to differing scales.
"""

import logging
from datetime import date, datetime

import numpy as np

from app.ml.content_model import ContentBasedRecommender
from app.ml.semantic_model import SemanticRecommender
from app.ml.personalization import build_preference_vector, get_user_signal_weights

logger = logging.getLogger("streamsync")

# Configurable hybrid weights — must sum to 1.0 for scores to stay in [0, 1]
WEIGHTS = {
    "content_sim": 0.20,
    "semantic_sim": 0.20,
    "user_pref": 0.25,
    "rating": 0.15,
    "popularity": 0.10,
    "trending": 0.05,
    "recency": 0.05,
}


def _normalize(values: np.ndarray) -> np.ndarray:
    """Min-max normalize to [0, 1]. Returns zeros if all values are identical."""
    v_min, v_max = values.min(), values.max()
    if v_max == v_min:
        return np.zeros_like(values)
    return (values - v_min) / (v_max - v_min)


def _recency_score(release_date_str: str | None) -> float:
    """Newer content scores higher. No release date -> 0."""
    if not release_date_str:
        return 0.0
    try:
        release = datetime.strptime(release_date_str, "%Y-%m-%d").date()
    except ValueError:
        return 0.0
    days_old = (date.today() - release).days
    if days_old < 0:
        days_old = 0  # future release dates (upcoming content)
    # Decay: full score at 0 days old, ~0 by 3 years (1095 days)
    return max(0.0, 1.0 - (days_old / 1095))


class HybridRecommender:
    def __init__(self) -> None:
        self.content_model = ContentBasedRecommender()
        self.semantic_model = SemanticRecommender()
        self._fitted = False

    def fit(self) -> None:
        logger.info("Fitting hybrid recommender (content-based + semantic)...")
        self.content_model.fit()
        self.semantic_model.fit(persist=False)  # embeddings already persisted once
        self._fitted = True

    def _explain(
        self, row, content_sim: float, semantic_sim: float, user_pref: float, is_cold_start: bool
    ) -> str:
        """Generate a human-readable explanation for why this was recommended."""
        reasons = []
        if user_pref > 0.5 and not is_cold_start:
            reasons.append("matches your taste based on what you've watched and rated highly")
        if content_sim > 0.15:
            reasons.append("shares genres, cast, or themes with titles you like")
        if semantic_sim > 0.3:
            reasons.append("has a similar story or tone to content you've engaged with")
        if row.get("provider_rating", 0) and row["provider_rating"] >= 7.5:
            reasons.append(f"highly rated ({row['provider_rating']}/10)")
        if row.get("popularity", 0) and row["popularity"] > 200:
            reasons.append("currently popular")

        if not reasons:
            return "Recommended based on overall popularity and ratings."
        return "Recommended because it " + "; and ".join(reasons) + "."

    def recommend_for_user(self, user_id: str, top_n: int = 10) -> list[dict]:
        """
        Full hybrid recommendation for a specific user. Falls back gracefully
        to a non-personalized (popularity/rating/trending-weighted) list if
        the user has no interaction history yet (cold start).
        """
        if not self._fitted:
            raise RuntimeError("Call fit() before recommend_for_user().")

        df = self.content_model.df
        if df is None or df.empty:
            return []

        n = len(df)

        # --- Content-based + semantic preference similarity ---
        content_pref_vector = build_preference_vector(
            user_id, self.content_model._id_to_index, self.content_model.tfidf_matrix.toarray()
        )
        semantic_pref_vector = build_preference_vector(
            user_id, self.semantic_model._id_to_index, self.semantic_model.embeddings
        )
        is_cold_start = content_pref_vector is None

        if content_pref_vector is not None:
            content_sim_scores = self.content_model.tfidf_matrix.toarray() @ content_pref_vector
        else:
            content_sim_scores = np.zeros(n)

        if semantic_pref_vector is not None:
            semantic_sim_scores = self.semantic_model.embeddings @ semantic_pref_vector
        else:
            semantic_sim_scores = np.zeros(n)

        # user_pref score is just the average of content+semantic personalized sim
        user_pref_scores = (content_sim_scores + semantic_sim_scores) / 2

        # --- Non-personalized signals ---
        rating_raw = df["provider_rating"].fillna(0).to_numpy(dtype=float)
        popularity_raw = df["popularity"].fillna(0).to_numpy(dtype=float)
        recency_raw = np.array([_recency_score(d) for d in df["release_date"]])
        # Trending: we don't have a separate stored trending_score column populated
        # yet (Phase 2 schema has the column; Phase 6 sync doesn't set it) — using
        # popularity as a documented proxy for now rather than fabricating a metric.
        trending_raw = popularity_raw.copy()

        content_sim_norm = _normalize(content_sim_scores)
        semantic_sim_norm = _normalize(semantic_sim_scores)
        user_pref_norm = _normalize(user_pref_scores)
        rating_norm = _normalize(rating_raw)
        popularity_norm = _normalize(popularity_raw)
        trending_norm = _normalize(trending_raw)
        recency_norm = _normalize(recency_raw)

        final_scores = (
            WEIGHTS["content_sim"] * content_sim_norm
            + WEIGHTS["semantic_sim"] * semantic_sim_norm
            + WEIGHTS["user_pref"] * user_pref_norm
            + WEIGHTS["rating"] * rating_norm
            + WEIGHTS["popularity"] * popularity_norm
            + WEIGHTS["trending"] * trending_norm
            + WEIGHTS["recency"] * recency_norm
        )

        # Exclude items the user has already interacted with (don't recommend
        # something they've already watched/rated/favorited)
        already_seen = set(get_user_signal_weights(user_id).keys())

        ranked_indices = np.argsort(final_scores)[::-1]

        results = []
        for idx in ranked_indices:
            row = df.iloc[idx]
            if row["id"] in already_seen:
                continue
            results.append(
                {
                    "content_id": row["id"],
                    "title": row["title"],
                    "final_score": round(float(final_scores[idx]), 4),
                    "explanation": self._explain(
                        row,
                        content_sim_norm[idx],
                        semantic_sim_norm[idx],
                        user_pref_norm[idx],
                        is_cold_start,
                    ),
                }
            )
            if len(results) >= top_n:
                break

        return results