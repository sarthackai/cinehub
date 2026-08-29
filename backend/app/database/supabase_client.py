from functools import lru_cache

from supabase import create_client, Client

from app.core.config import settings


@lru_cache
def get_supabase_client() -> Client:
    """
    Backend-only Supabase client using the service_role key.
    This bypasses Row Level Security by design — the FastAPI layer
    is responsible for enforcing authorization before calling this.
    NEVER expose this client or its key to the frontend.
    """
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)