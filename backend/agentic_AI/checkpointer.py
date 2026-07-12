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


@contextmanager
def get_checkpointer():
    """
    Yields a RedisSaver instance connected to Upstash via TCP (rediss://).

    The `rediss://` scheme enables SSL automatically through redis-py.
    Always use this as a context manager so the connection is closed cleanly.

    Example:
        with get_checkpointer() as cp:
            graph = builder.compile(checkpointer=cp)
    """
    client = redis.Redis.from_url(
        settings.REDIS_URL,
        decode_responses=False,   # RedisSaver needs binary-safe responses
    )
    saver = RedisSaver(client)
    try:
        yield saver
    finally:
        client.close()
