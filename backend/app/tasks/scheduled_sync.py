"""
Background scheduled sync job. Runs periodically while the FastAPI server
is up, using a more persistent retry policy (5 attempts) since nothing is
waiting on the response synchronously. Automatically refits the recommendation
model afterward so newly synced content (new releases, trending shifts, etc.)
is actually reflected in recommendations without requiring a manual step.
"""

import logging

from app.services.content_service import ContentSyncService
from app.ml.model_registry import refit_model

logger = logging.getLogger("streamsync")


def scheduled_full_sync() -> None:
    logger.info("Starting scheduled full content sync...")
    service = ContentSyncService(max_retries=5)
    result = service.run_full_sync(include_credits=False)
    logger.info(
        "Scheduled sync complete: %s/%s jobs succeeded, %s rows processed",
        result["jobs_run"] - result["jobs_failed"],
        result["jobs_run"],
        result["total_rows_processed"],
    )

    if result["total_rows_processed"] > 0:
        logger.info("Refitting recommendation model with newly synced content...")
        refit_model()
        logger.info("Model refit complete after scheduled sync.")
    else:
        logger.info("No new rows processed — skipping model refit.")