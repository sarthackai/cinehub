from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    ENVIRONMENT: str = "development"

    SUPABASE_URL: str
    SUPABASE_ANON_KEY: str
    SUPABASE_SERVICE_ROLE_KEY: str
    CONTENT_METADATA_API_KEY: str = ""
    BACKEND_API_URL: str = "http://127.0.0.1:8000"
    FRONTEND_URL: str = "http://localhost:5173"
    MODEL_PATH: str = "./ml_pipeline/artifacts"
    EMBEDDING_MODEL_NAME: str = "all-MiniLM-L6-v2"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()