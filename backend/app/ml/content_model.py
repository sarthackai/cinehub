"""
Content-based recommendation model using TF-IDF + cosine similarity over the
"soup" text built in preprocessing.py.

Design notes:
- We keep the model in memory (no persistence yet) since 108 rows is tiny;
  Phase 16 (deployment) or scale-up would persist via joblib if the catalog
  grows large enough that rebuilding on every startup becomes slow.
- Similarity is computed as a full pairwise matrix (NxN) since N is small.
  For a catalog of thousands+, this would need to move to approximate nearest
  neighbor search (e.g. via a vector index) — noted here rather than hidden.
"""

import logging

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app.ml.preprocessing import load_and_preprocess_content

logger = logging.getLogger("streamsync")


class ContentBasedRecommender:
    def __init__(self) -> None:
        self.df: pd.DataFrame | None = None
        self.tfidf_matrix = None
        self.similarity_matrix: np.ndarray | None = None
        self.vectorizer: TfidfVectorizer | None = None
        self._id_to_index: dict[str, int] = {}

    def fit(self) -> None:
        """Load content, vectorize, and compute the full pairwise similarity matrix."""
        self.df = load_and_preprocess_content()

        if self.df.empty:
            logger.warning("No content to fit the content-based model on.")
            return

        self.vectorizer = TfidfVectorizer(
            stop_words="english",
            max_features=5000,  # cap vocabulary size; plenty for a catalog this size
            ngram_range=(1, 2),  # unigrams + bigrams capture phrases like "sci fi"
        )
        self.tfidf_matrix = self.vectorizer.fit_transform(self.df["soup"])
        self.similarity_matrix = cosine_similarity(self.tfidf_matrix)

        self._id_to_index = {content_id: idx for idx, content_id in enumerate(self.df["id"])}

        logger.info(
            "Content-based model fitted: %d items, %d vocabulary terms.",
            len(self.df),
            len(self.vectorizer.vocabulary_),
        )

    def get_similar(self, content_id: str, top_n: int = 10) -> list[dict]:
        """Return the top_n most similar items to the given content_id."""
        if self.df is None or self.similarity_matrix is None:
            raise RuntimeError("Model has not been fitted. Call fit() first.")

        idx = self._id_to_index.get(content_id)
        if idx is None:
            logger.warning("content_id %s not found in fitted model.", content_id)
            return []

        scores = list(enumerate(self.similarity_matrix[idx]))
        # Exclude the item itself (always similarity=1.0 with itself)
        scores = [s for s in scores if s[0] != idx]
        scores.sort(key=lambda x: x[1], reverse=True)
        top_scores = scores[:top_n]

        results = []
        for i, score in top_scores:
            row = self.df.iloc[i]
            results.append(
                {
                    "content_id": row["id"],
                    "title": row["title"],
                    "poster_url": row.get("poster_url"),
                    "similarity_score": round(float(score), 4),
                }
            )
        return results