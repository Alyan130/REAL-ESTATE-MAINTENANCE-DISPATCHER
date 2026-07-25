"""
app/main.py

Application factory.

Run with `uvicorn app.main:app --reload` from `backend/`.
"""
from fastapi import FastAPI

from app.api.router import api_router
from app.core.logging import configure_logging
from app.exceptions import register_exception_handlers
from app.middleware import register_middleware


def create_app() -> FastAPI:
    """Build the application. Wiring only — every behaviour lives in its module."""
    configure_logging()

    app = FastAPI(
        title="Real Estate Maintenance Dispatcher",
        version="1.0.0",
    )

    register_middleware(app)
    register_exception_handlers(app)
    app.include_router(api_router)

    return app


app = create_app()
