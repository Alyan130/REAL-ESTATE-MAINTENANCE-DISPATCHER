from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolve .env relative to this file so it works from any cwd
_ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


class Settings(BaseSettings):
    """Application settings loaded from environment variables / .env file."""

    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Database
    DATABASE_URL: str
    DIRECT_URL: str = ""

    # JWT
    JWT_SECRET_KEY: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"

    # bcrypt work factor (cost)
    BCRYPT_WORK_FACTOR: int = 12

    # Resend (email)
    RESEND_API_KEY: str = ""

    # Frontend base URL (used for invite links)
    BASE_URL: str = "https://resend.dev"

    # Browser origins allowed to call this API (comma-separated).
    # The frontend is a separate origin, so without this every request is
    # blocked by CORS before it reaches a route.
    CORS_ORIGINS: str = "http://localhost:3000"

    @property
    def cors_origins_list(self) -> list[str]:
        """CORS_ORIGINS parsed into a list, with blanks dropped."""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    # Supabase Storage
    SUPABASE_URL: str = ""
    SUPABASE_KEY: str = ""
    SUPABASE_STORAGE_BUCKET: str = "tickets"

    # LangSmith Tracing
    LANGSMITH_TRACING: bool = True
    LANGSMITH_ENDPOINT: str = "https://api.smith.langchain.com"
    LANGSMITH_API_KEY: str = ""
    LANGSMITH_PROJECT: str = ""

    # Redis (Upstash TCP)
    REDIS_URL: str = ""

    # OpenAI
    OPENAI_API_KEY: str = ""


settings = Settings()
