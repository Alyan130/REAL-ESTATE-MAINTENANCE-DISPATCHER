"""
app/main.py

Application factory.

Run with `uvicorn app.main:app --reload` from `backend/`.
"""
import logging

from fastapi import FastAPI

from app.api.router import api_router
from app.core.logging import configure_logging
from app.exceptions import register_exception_handlers
from app.middleware import register_middleware

logger = logging.getLogger(__name__)


def _register_inngest(app: FastAPI) -> None:
    """
    Serve the Inngest endpoint, if Inngest is configured.

    Deliberately outside the JWT — it is authenticated by Inngest's own HMAC
    signature, and a bearer-token guard here would reject every timer.

    Wrapped in try/except because follow-up timers are an enhancement, not a
    dependency: a missing key or an unreachable dev server must not stop the API
    from booting.
    """
    try:
        from app.core.queue import get_client
        from app.jobs.negotiation_jobs import INNGEST_FUNCTIONS

        client = get_client()
        if client is None or not INNGEST_FUNCTIONS:
            logger.info("Inngest not configured — follow-up timers are disabled")
            return

        import inngest.fast_api

        inngest.fast_api.serve(app, client, INNGEST_FUNCTIONS, serve_path="/api/inngest")
        logger.info("Inngest mounted at /api/inngest")
    except Exception:
        logger.exception("Could not mount Inngest — follow-up timers are disabled")


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
    _register_inngest(app)

    return app


app = create_app()
