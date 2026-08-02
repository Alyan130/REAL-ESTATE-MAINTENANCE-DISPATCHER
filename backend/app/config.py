import os
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

    # ─── LLM provider ────────────────────────────────────────────────────────
    # "openai" or "openrouter". Both speak the OpenAI wire format, so switching
    # is a base URL and a key — see agentic_AI/llm.py.
    LLM_PROVIDER: str = "openai"
    # Model id, in whichever provider's namespace LLM_PROVIDER selects
    # (e.g. "gpt-4o" for openai, "google/gemma-3-27b-it" for openrouter).
    LLM_MODEL: str = "gpt-4o"
    LLM_TEMPERATURE: float = 0.0
    # Blank keeps LangChain's default (function-calling). Set to "json_schema"
    # for a model that cannot do tool-calling — otherwise structured output
    # silently returns an empty object and Pydantic fills it with defaults.
    LLM_STRUCTURED_METHOD: str = ""

    OPENAI_API_KEY: str = ""

    OPENROUTER_API_KEY: str = ""
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"

    # Inngest — durable timers for negotiation follow-ups.
    # With none of these set, follow-ups are simply never scheduled: the
    # negotiation still works, a silent vendor just isn't chased.
    INNGEST_APP_ID: str = "dispatcher"
    INNGEST_EVENT_KEY: str = ""
    INNGEST_SIGNING_KEY: str = ""
    INNGEST_DEV: bool = True


settings = Settings()


def _export_sdk_env() -> None:
    """
    Copy the SDK-read settings into `os.environ`.

    `pydantic-settings` reads `.env` into *this object* and nothing else — it
    never touches `os.environ`. Both the OpenAI client and the LangSmith tracer
    read `os.environ` directly and have no other source, so without this the
    keys sit here where neither of them looks: every `ChatOpenAI` call raises
    for a missing key, and `tracing_is_enabled()` stays False no matter what
    `LANGSMITH_TRACING` says.

    An already-set variable wins, so a real shell export (CI, container, or
    `LANGSMITH_PROJECT=... uvicorn ...`) is never overwritten by the .env file.
    """
    exports = {
        "OPENAI_API_KEY": settings.OPENAI_API_KEY,
    }

    # Only advertise tracing when there is a key to trace with. Setting
    # LANGSMITH_TRACING=true without a key makes every LLM call attempt an
    # export that fails and logs, which is noisier than not tracing at all.
    if settings.LANGSMITH_TRACING and settings.LANGSMITH_API_KEY:
        exports.update(
            {
                "LANGSMITH_TRACING": "true",
                "LANGSMITH_ENDPOINT": settings.LANGSMITH_ENDPOINT,
                "LANGSMITH_API_KEY": settings.LANGSMITH_API_KEY,
                "LANGSMITH_PROJECT": settings.LANGSMITH_PROJECT,
            }
        )

    for key, value in exports.items():
        if value and not os.environ.get(key):
            os.environ[key] = value


_export_sdk_env()
