"""
app/agentic_AI/llm.py

One place that builds the chat model, so the provider is a setting rather than a
literal repeated at every call site.

Both providers speak the OpenAI wire format, so `ChatOpenAI` serves both — the
difference is a base URL, a key, and the model id. That is the whole reason this
is a config switch and not two client classes: swapping `LLM_PROVIDER` in `.env`
changes the provider with no code change and no import change.

Structured output is the one place they genuinely differ. `with_structured_output`
defaults to OpenAI function-calling, which many OpenRouter-hosted models do not
implement — the call fails, or worse returns an empty object that Pydantic fills
with defaults. `LLM_STRUCTURED_METHOD` exists so a model without tool support can
be pointed at `json_schema` instead of being unusable.
"""
from __future__ import annotations

import logging
from typing import Any

from langchain_openai import ChatOpenAI

from app.config import settings

logger = logging.getLogger(__name__)

OPENROUTER = "openrouter"
OPENAI = "openai"


def _provider() -> str:
    return (settings.LLM_PROVIDER or OPENAI).strip().lower()


def get_chat_model(*, temperature: float | None = None, **overrides: Any) -> ChatOpenAI:
    """
    The chat model configured in `.env`.

    `temperature` defaults to `LLM_TEMPERATURE` (0), because every call in this
    codebase is a classification or an extraction — both want the same answer for
    the same input, twice.
    """
    provider = _provider()
    temp = settings.LLM_TEMPERATURE if temperature is None else temperature

    kwargs: dict[str, Any] = {
        "model": settings.LLM_MODEL,
        "temperature": temp,
    }

    if provider == OPENROUTER:
        if not settings.OPENROUTER_API_KEY:
            raise RuntimeError(
                "LLM_PROVIDER=openrouter but OPENROUTER_API_KEY is not set in backend/.env"
            )
        kwargs["api_key"] = settings.OPENROUTER_API_KEY
        kwargs["base_url"] = settings.OPENROUTER_BASE_URL
        # OpenRouter attributes traffic by these and they show on the dashboard.
        # Optional to the API, useful when one key serves several things.
        kwargs["default_headers"] = {
            "HTTP-Referer": settings.BASE_URL,
            "X-Title": "Real Estate Maintenance Dispatcher",
        }
    elif provider == OPENAI:
        if not settings.OPENAI_API_KEY:
            raise RuntimeError(
                "LLM_PROVIDER=openai but OPENAI_API_KEY is not set in backend/.env"
            )
        kwargs["api_key"] = settings.OPENAI_API_KEY
    else:
        raise RuntimeError(
            f"Unknown LLM_PROVIDER {provider!r} — expected 'openai' or 'openrouter'"
        )

    kwargs.update(overrides)
    return ChatOpenAI(**kwargs)


def get_structured_model(schema: type, **overrides: Any):
    """
    A chat model that returns `schema`.

    Every structured call in the graph goes through here so the method is chosen
    once. `LLM_STRUCTURED_METHOD` is honoured only when set — leaving it blank
    keeps LangChain's own default, which is correct for OpenAI and for any
    OpenRouter model that supports tool-calling.
    """
    llm = get_chat_model(**overrides)
    method = (settings.LLM_STRUCTURED_METHOD or "").strip()
    if method:
        return llm.with_structured_output(schema, method=method)
    return llm.with_structured_output(schema)


def describe_model() -> str:
    """Provider and model, for a startup log line — never the key."""
    return f"{_provider()}:{settings.LLM_MODEL}"
