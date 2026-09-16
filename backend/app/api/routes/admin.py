from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.security import require_admin
from app.services.content_service import ContentSyncService
from app.ml.model_registry import refit_model

router = APIRouter(prefix="/api/admin", tags=["admin"])


class SyncRequest(BaseModel):
    job_name: str
    content_type: str = "movie"
    include_credits: bool = False


@router.post("/sync")
def trigger_sync(payload: SyncRequest, _admin_user: str = Depends(require_admin)):
    service = ContentSyncService()
    result = service.run_sync(
        job_name=payload.job_name,
        content_type=payload.content_type,
        include_credits=payload.include_credits,
    )
    if result["status"] in ("success", "partial") and result["rows_processed"] > 0:
        refit_model()
    return result