from fastapi import FastAPI, Depends

from app.api.routes import auth
from app.core.security import get_current_user_id

app = FastAPI(title="StreamSync AI Backend")

app.include_router(auth.router)


@app.get("/")
def read_root():
    return {"status": "ok", "message": "StreamSync AI backend is running"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}


@app.get("/api/auth/me")
def get_me(user_id: str = Depends(get_current_user_id)):
    return {"user_id": user_id}