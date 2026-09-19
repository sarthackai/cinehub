import logging
from contextlib import asynccontextmanager

from app.api.routes import recommendations
from app.ml.model_registry import get_model
from app.api.routes import interactions
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from apscheduler.schedulers.background import BackgroundScheduler
from app.api.routes import user

from app.api.routes import auth, content, admin
from app.core.config import settings
from app.core.security import get_current_user_id
from app.core.exceptions import (
    http_exception_handler,
    validation_exception_handler,
    unhandled_exception_handler,
)
from app.tasks.scheduled_sync import scheduled_full_sync

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

logger = logging.getLogger("streamsync")

scheduler = BackgroundScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: schedule the recurring sync job.
    # Every 6 hours is a reasonable default for a portfolio project — frequent
    # enough to feel "live", infrequent enough to respect TMDB's rate limits.
    scheduler.add_job(
        scheduled_full_sync,
        trigger="interval",
        hours=6,
        id="full_content_sync",
        replace_existing=True,
        next_run_time=None,  # don't run immediately on startup; first run is 6h out
    )
    scheduler.start()
    logger.info("Background scheduler started — full sync every 6 hours.")
    # Fit the recommendation model once at startup (not per-request — expensive)
    logger.info("Fitting recommendation model at startup...")
    get_model()
    logger.info("Recommendation model ready.")
    yield

    # Shutdown: stop the scheduler cleanly.
    scheduler.shutdown()
    logger.info("Background scheduler stopped.")


app = FastAPI(
    title="StreamSync AI Backend",
    docs_url="/docs" if settings.ENVIRONMENT == "development" else None,
    redoc_url="/redoc" if settings.ENVIRONMENT == "development" else None,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)

app.include_router(auth.router)
app.include_router(content.router)
app.include_router(admin.router)
app.include_router(recommendations.router)
app.include_router(interactions.router)
app.include_router(user.router)

@app.get("/")
def read_root():
    return {"status": "ok", "message": "StreamSync AI backend is running"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}


@app.get("/api/auth/me")
def get_me(user_id: str = Depends(get_current_user_id)):
    return {"user_id": user_id}
