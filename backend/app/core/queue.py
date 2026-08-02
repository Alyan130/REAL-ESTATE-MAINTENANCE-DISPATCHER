"""
core/queue.py

Durable timers, via Inngest.

**Why not LangGraph.** A paused graph is not running. `interrupt()` writes state
to Redis and the process exits — nothing is counting down, and nothing wakes it.
Something external has to call resume. LangGraph is a state machine, not a job
queue, and a negotiation needs to chase a vendor who has said nothing for two
days across an app redeploy.

**Why not a sleeping task.** `asyncio.sleep(36 * 3600)` holds the clock in our
process. A Railway redeploy loses every pending timer silently.
`step.sleep_until` hands the clock to Inngest; the container can restart
mid-sleep and the timer still fires.

Emission is fire-and-forget, same discipline as `core/email.py`: a timer that
fails to arm must never roll back the negotiation turn that armed it.
"""
from __future__ import annotations

import logging

from app.config import settings

logger = logging.getLogger(__name__)

_client = None


def get_client():
    """
    The Inngest client, built lazily.

    Lazy because `inngest` is an optional dependency in practice: without
    credentials the negotiation still works end-to-end, it simply never chases a
    silent vendor. That degradation is worth keeping — an import-time failure
    here would take down the whole app over a follow-up timer.
    """
    global _client
    if _client is not None:
        return _client

    if not settings.INNGEST_EVENT_KEY and not settings.INNGEST_DEV:
        return None

    try:
        import inngest
    except ModuleNotFoundError:
        # Not installed — an expected state, not a fault. `pip install inngest`
        # when follow-up timers are wanted.
        logger.info("inngest is not installed — follow-up timers are disabled")
        return None

    try:
        _client = inngest.Inngest(
            app_id=settings.INNGEST_APP_ID,
            event_key=settings.INNGEST_EVENT_KEY or None,
            signing_key=settings.INNGEST_SIGNING_KEY or None,
            is_production=not settings.INNGEST_DEV,
            logger=logger,
        )
        return _client
    except Exception:
        logger.exception("Could not build the Inngest client — timers are disabled")
        return None


async def emit(name: str, data: dict) -> None:
    """Send an event. Logs and swallows every failure."""
    client = get_client()
    if client is None:
        logger.info("Inngest not configured — dropping event %s", name)
        return

    try:
        import inngest

        await client.send(inngest.Event(name=name, data=data))
        logger.info("Emitted %s", name)
    except Exception:
        logger.exception("Failed to emit %s", name)
