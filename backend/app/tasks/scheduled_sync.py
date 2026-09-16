"""
Background scheduled sync job. Runs periodically while the FastAPI server
is up, using a more persistent retry policy (5 attempts) since nothing is
waiting on the response synchronously.
"""

import logging

from app.services.content_service import ContentSyncService

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