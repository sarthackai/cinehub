"""
Holds a single, shared, lazily-initialized HybridRecommender instance for the
life of the server process. Fitting the model (embedding generation, TF-IDF,
similarity matrices) is expensive enough that we do it once at startup and
after each content sync, not on every API request.
"""

import logging
import threading

from app.ml.hybrid_recommender import HybridRecommender

logger = logging.getLogger("streamsync")

_model: HybridRecommender | None = None
_lock = threading.Lock()


def get_model() -> HybridRecommender:
    """Returns the shared fitted model, fitting it on first access if needed."""
    global _model
    with _lock:
        if _model is None:
            logger.info("Model registry: no cached model, fitting now...")
            _model = HybridRecommender()
            _model.fit()
        return _model


def refit_model() -> None:
    """Force a refit — call this after a content sync adds/changes data."""
    global _model
    with _lock:
        logger.info("Model registry: refitting model...")
        new_model = HybridRecommender()
        new_model.fit()
        _model = new_model