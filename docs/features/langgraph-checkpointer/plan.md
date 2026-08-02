# LangGraph Checkpointer Plan — Postgres

> Supersedes the original Redis/Upstash plan. The directory name is historical.

## Context
LangGraph needs a checkpointer to persist `TicketState` while a graph is paused at
an `interrupt()` — the PM approval gate and both negotiation waits. Without one,
`interrupt()` raises and no human-in-the-loop step can work at all.

The original plan used `langgraph-checkpoint-redis` against Upstash. That does not
work, for three separate reasons found when the stack was first run against live
infrastructure.

## Why Redis was abandoned

1. **Upstash cannot host it.** `langgraph-checkpoint-redis` is built on RediSearch.
   Upstash exposes RedisJSON but not `FT.*` — verified directly: `ping` ✓,
   `JSON.SET` ✓, `FT._LIST` rejected by Upstash with a compatibility notice.
2. **The TTL was shorter than the workflow.** The Redis saver ran a 3-day expiry,
   while a P4 negotiation window is longer. That made `_negotiate_from_db` and
   `_dispatch_from_db` — written as disaster paths — the *routine* path for slow
   tickets.
3. **A paused ticket is business state.** It belongs in the database that already
   holds the ticket, not in a cache priced by memory.

## Approach & Decisions

1. **`AsyncPostgresSaver`, not `PostgresSaver`.** Every graph call in this codebase
   is `await graph.ainvoke(...)`, and the **synchronous** savers do not implement
   the async methods — `BaseCheckpointSaver.aget_tuple` raises
   `NotImplementedError`. A sync saver fails on the first awaited invocation
   regardless of the database behind it. This was true of the previous `RedisSaver`
   wiring too, and is why `get_checkpointer` is now an **async** context manager.
2. **`DIRECT_URL`, not `DATABASE_URL`.** The saver uses server-side prepared
   statements, which a transaction-mode pooler does not support. The symptom is an
   intermittent `DuplicatePreparedStatement` under concurrency rather than a clean
   startup failure. `normalise_dsn` strips the Prisma-only params either way.
3. **No TTL.** Paused workflows persist until resolved. The rebuild-from-database
   paths stay in place, but become genuine recovery rather than routine.
4. **`setup()` once per process.** It is idempotent DDL, but it is still a round
   trip, and `get_checkpointer` is called on every graph invocation.
5. **Redis is retained for the resume lock only.** `_acquire_lock` is plain
   `SET NX EX`, needs no modules, and works on any Redis including Upstash.
6. **Windows event loop.** psycopg's async driver cannot run on Windows'
   default `ProactorEventLoop`. The policy is set to `WindowsSelectorEventLoopPolicy`
   at import of `checkpointer.py`, gated on `sys.platform == "win32"`, because
   `asyncio.run()` in the background tasks builds its loop from that policy.

## Verified
- Saver connects to Supabase and creates its tables.
- A graph pauses at `interrupt()`, and **a separate connection and saver instance**
  sees it still paused and resumes it to completion — the property the PM approval
  gate depends on.
