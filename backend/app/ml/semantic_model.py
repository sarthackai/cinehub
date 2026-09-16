"""
Semantic recommendation model using Sentence Transformers to generate dense
embeddings for each content item, enabling meaning-based similarity search
that goes beyond keyword overlap (e.g. "space exploration and time travel"
matching "astronauts exploring the universe").

Design notes:
- We embed the overview text specifically (not the full "soup"), since
  Sentence Transformers are trained on natural language sentences, and
  feeding it a keyword-stuffed soup would work against its strengths.
  Genre/cast context is still available separately via ContentBasedRecommender
  and gets combined at the hybrid-ranking layer (Phase 10).
- Embeddings are also persisted into Supabase's content_embeddings table
  (Phase 2 schema) so they don't need to be recomputed from scratch on every
  server restart — though we still keep an in-memory copy for fast similarity
  search within a running process.
"""

import logging

import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

from app.core.config import settings
from app.database.supabase_client import get_supabase_client
from app.ml.preprocessing import load_and_preprocess_content

logger = logging.getLogger("streamsync")


class SemanticRecommender:
    def __init__(self) -> None:
        self.model = SentenceTransformer(settings.EMBEDDING_MODEL_NAME)
        self.df: pd.DataFrame | None = None
        self.embeddings: np.ndarray | None = None
        self.similarity_matrix: np.ndarray | None = None
        self._id_to_index: dict[str, int] = {}

    def fit(self, persist: bool = True) -> None:
        """Load content, embed overviews, compute similarity matrix."""
        self.df = load_and_preprocess_content()

        if self.df.empty:
            logger.warning("No content to fit the semantic model on.")
            return

        # Use overview text (fall back to title if overview is empty)
        texts = [
            row["overview"] if row["overview"].strip() else row["title"]
            for _, row in self.df.iterrows()
        ]

        logger.info("Encoding %d items with sentence-transformers...", len(texts))
        self.embeddings = self.model.encode(texts, show_progress_bar=False)
        self.similarity_matrix = cosine_similarity(self.embeddings)

        self._id_to_index = {content_id: idx for idx, content_id in enumerate(self.df["id"])}

        logger.info("Semantic model fitted: %d items embedded.", len(self.df))

        if persist:
            self._persist_embeddings()

    def _persist_embeddings(self) -> None:
        """Save embeddings to Supabase so they can be reused without recomputing."""
        client = get_supabase_client()
        rows = []
        for idx, content_id in enumerate(self.df["id"]):
            rows.append(
                {
                    "content_id": content_id,
                    "model_name": settings.EMBEDDING_MODEL_NAME,
                    "embedding": self.embeddings[idx].tolist(),
                }
            )
        # Upsert in batches to avoid oversized single requests
        batch_size = 50
        for i in range(0, len(rows), batch_size):
            batch = rows[i : i + batch_size]
            client.table("content_embeddings").upsert(
                batch, on_conflict="content_id"
            ).execute()
        logger.info("Persisted %d embeddings to content_embeddings.", len(rows))

    def get_similar(self, content_id: str, top_n: int = 10) -> list[dict]:
        """Return the top_n most semantically similar items."""
        if self.df is None or self.similarity_matrix is None:
            raise RuntimeError("Model has not been fitted. Call fit() first.")

        idx = self._id_to_index.get(content_id)
        if idx is None:
            logger.warning("content_id %s not found in fitted model.", content_id)
            return []

        scores = list(enumerate(self.similarity_matrix[idx]))
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
                    "similarity_score": round(float(score), 4),
                }
            )
        return results

    def search_by_text(self, query: str, top_n: int = 10) -> list[dict]:
        """
        Semantic search: embed a free-text query and find the most similar
        content by meaning, not exact keywords. This is what powers natural
        language search like 'space exploration and time travel'.
        """
        if self.df is None or self.embeddings is None:
            raise RuntimeError("Model has not been fitted. Call fit() first.")

        query_embedding = self.model.encode([query])
        scores = cosine_similarity(query_embedding, self.embeddings)[0]

        ranked = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)[:top_n]

        results = []
        for i, score in ranked:
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