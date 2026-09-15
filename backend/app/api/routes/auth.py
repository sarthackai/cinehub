from fastapi import APIRouter, HTTPException, status
from supabase import create_client

from app.core.config import settings
from app.database.supabase_client import get_supabase_client
from app.schemas.auth import SignUpRequest, LoginRequest, AuthResponse

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _get_auth_client():
    """
    Fresh, non-cached client for auth operations only. Deliberately NOT the
    shared service-role client from get_supabase_client() — signing in on
    that shared client mutates its session and silently downgrades every
    other .table() call in the app from service_role to the logged-in
    user's own (RLS-restricted) JWT. This keeps auth flows isolated from
    the backend's privileged database client.
    """
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)


@router.post("/signup", response_model=AuthResponse)
def signup(payload: SignUpRequest):
    auth_client = _get_auth_client()
    try:
        result = auth_client.auth.sign_up(
            {
                "email": payload.email,
                "password": payload.password,
            }
        )
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    if result.user is None or result.session is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Signup failed — check if email confirmation is required.",
        )

    # Profile creation uses the privileged service-role client (unaffected by
    # the auth_client above, since they're separate instances).
    service_client = get_supabase_client()
    service_client.table("profiles").insert(
        {
            "id": result.user.id,
            "display_name": payload.display_name or payload.email.split("@")[0],
        }
    ).execute()

    return AuthResponse(
        access_token=result.session.access_token,
        refresh_token=result.session.refresh_token,
        user_id=result.user.id,
        email=result.user.email,
    )


@router.post("/login", response_model=AuthResponse)
def login(payload: LoginRequest):
    auth_client = _get_auth_client()
    try:
        result = auth_client.auth.sign_in_with_password(
            {
                "email": payload.email,
                "password": payload.password,
            }
        )
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc))

    return AuthResponse(
        access_token=result.session.access_token,
        refresh_token=result.session.refresh_token,
        user_id=result.user.id,
        email=result.user.email,
    )