"""
checkpointer.py
──────────────
LangGraph persistence, backed by the project's own Postgres.

Usage (note: **async** context manager):

    from app.agentic_AI.checkpointer import get_checkpointer

    async with get_checkpointer() as checkpointer:
        graph = builder.compile(checkpointer=checkpointer)
        await graph.ainvoke(state, {"configurable": {"thread_id": ticket_id}})

Why Postgres and not Redis
──────────────────────────
A paused graph is business state — a ticket waiting on a property manager — and
it belongs in the database that already holds the ticket, not in a cache with an
expiry shorter than the workflow it guards. The Redis implementation carried a
3-day TTL, while a P4 negotiation window is longer than that, which made
`_negotiate_from_db` / `_dispatch_from_db` the *routine* path for slow tickets
rather than the disaster path they were written as. With no TTL, those become
what they were meant to be.

Upstash also cannot host the Redis saver at all: `langgraph-checkpoint-redis` is
built on RediSearch, and Upstash exposes RedisJSON but not `FT.*`.

Redis is still used — for the per-thread resume lock in
`services/negotiation_service.py`, which is plain `SET NX EX` and needs no
modules.
"""

from contextlib import asynccontextmanager

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from app.agentic_AI.runtime import run_async  # noqa: F401  (re-export; sets the loop policy)
from app.config import settings
from app.database import normalise_dsn

# The Windows event-loop constraint that this module's driver imposes lives in
# `runtime.py`, alongside the `run_async` that satisfies it. It is NOT enough to
# set the policy here: every caller imports this module lazily from inside the
# coroutine, by which point `asyncio.run()` has already built the wrong loop.
# Entry points must use `run_async`, never `asyncio.run`.

# `setup()` issues CREATE TABLE IF NOT EXISTS. It is idempotent but it is still a
# round trip of DDL, and this runs on every graph invocation — so do it once per
# process instead of once per ticket.
_setup_done = False


def checkpointer_dsn() -> str:
    """
    The connection string the saver uses.

    **DIRECT_URL is preferred over DATABASE_URL on purpose.** The saver relies on
    server-side prepared statements, which a transaction-mode pooler (pgbouncer,
    which is what Supabase's pooled URL is) does not support — the symptom is an
    intermittent `DuplicatePreparedStatement` under concurrency, not a clean
    failure at startup. `normalise_dsn` strips the Prisma-only params Supabase
    ships in that URL, exactly as the SQLAlchemy engine does.
    """
    return normalise_dsn(settings.DIRECT_URL or settings.DATABASE_URL)


@asynccontextmanager
async def get_checkpointer():
    """
    Yields an `AsyncPostgresSaver`.

    Async, not sync, and that is load-bearing: every graph call in this codebase
    is `await graph.ainvoke(...)`, and the **synchronous** savers do not
    implement the async checkpoint methods — `BaseCheckpointSaver.aget_tuple`
    raises `NotImplementedError`. A sync saver here fails on the first awaited
    invocation, no matter which database is behind it.
    """
    global _setup_done

    async with AsyncPostgresSaver.from_conn_string(checkpointer_dsn()) as saver:
        if not _setup_done:
            await saver.setup()
            _setup_done = True
        yield saver
