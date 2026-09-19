import jwt
from jwt import PyJWKClient
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.core.config import settings
from app.database.supabase_client import get_supabase_client

bearer_scheme = HTTPBearer()

# Supabase's JWKS endpoint — publishes the public keys used to verify tokens.
# PyJWKClient caches keys internally and refreshes them as needed, so this
# client is created once and reused, not re-fetched on every request.
_jwks_client = PyJWKClient(f"{settings.SUPABASE_URL}/auth/v1/.well-known/jwks.json")


def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> str:
    token = credentials.credentials
    try:
        signing_key = _jwks_client.get_signing_key_from_jwt(token)
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["ES256"],
            audience="authenticated",
            leeway=10,  # tolerate up to 10s of clock drift between this machine and Supabase
        )
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing user identity",
        )

    return user_id


def require_admin(user_id: str = Depends(get_current_user_id)) -> str:
    """Dependency that ensures the current user has is_admin=true on their profile."""
    client = get_supabase_client()
    result = client.table("profiles").select("is_admin").eq("id", user_id).execute()

    if not result.data or not result.data[0].get("is_admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )

    return user_id