"""
checkpointer.py
──────────────
LangGraph persistence layer using Upstash Redis over TCP.

Usage:
    from agentic_AI.checkpointer import get_checkpointer

    with get_checkpointer() as checkpointer:
        graph = builder.compile(checkpointer=checkpointer)
        graph.invoke(state, {"configurable": {"thread_id": ticket_id}})
"""

from contextlib import contextmanager

import redis
from langgraph.checkpoint.redis import RedisSaver

from core.config import settings

# Paused human-in-the-loop workflows (a ticket awaiting PM approval) live only in
# the checkpoint until resumed. Keep them resumable for 3 days so a PM has a
# realistic window to approve/reject before the checkpoint expires.
# langgraph-checkpoint-redis expresses TTL in MINUTES via a config dict.
CHECKPOINT_TTL_MINUTES = 3 * 24 * 60  # 3 days
CHECKPOINT_TTL = {"default_ttl": CHECKPOINT_TTL_MINUTES, "refresh_on_read": True}


@contextmanager
def get_checkpointer():
    """
    Yields a RedisSaver instance connected to Upstash via TCP (rediss://).

    The `rediss://` scheme enables SSL automatically through redis-py.
    Always use this as a context manager so the connection is closed cleanly.

    A 3-day TTL is set so paused approval workflows survive until the PM acts
    (see CHECKPOINT_TTL). `refresh_on_read` extends the window on each access.

    Example:
        with get_checkpointer() as cp:
            graph = builder.compile(checkpointer=cp)
    """
    client = redis.Redis.from_url(
        settings.REDIS_URL,
        decode_responses=False,   # RedisSaver needs binary-safe responses
    )
    saver = RedisSaver(client, ttl=CHECKPOINT_TTL)
    try:
        yield saver
    finally:
        client.close()
