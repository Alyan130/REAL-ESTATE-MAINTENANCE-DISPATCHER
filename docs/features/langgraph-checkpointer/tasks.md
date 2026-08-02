# Tasks — Postgres checkpointer

## Done
- [x] Install `langgraph-checkpoint-postgres` and `psycopg[binary,pool]`; add both to `requirements.txt`.
- [x] Rewrite `app/agentic_AI/checkpointer.py` to yield an `AsyncPostgresSaver`.
- [x] Make `get_checkpointer` an **async** context manager (`@asynccontextmanager`).
- [x] Point the saver at `DIRECT_URL` (falling back to `DATABASE_URL`) through `normalise_dsn`.
- [x] Run `setup()` once per process rather than per invocation.
- [x] Convert all five call sites to `async with` — `ticket_service.py` (3), `negotiation_service.py` (2).
- [x] Move the Redis CA/TLS handling into `negotiation_service._redis_client`, the only remaining Redis user.
- [x] Set `WindowsSelectorEventLoopPolicy` on win32 so psycopg's async driver can connect.
- [x] Drop the 3-day TTL and update the `_negotiate_from_db` docstring — it is a recovery path now, not the routine one.
- [x] Verify: saver connects, tables created, `interrupt()` pauses, and a **separate** saver instance resumes it.

## Remaining
- [ ] Remove `langgraph-checkpoint-redis` and `upstash-redis` from `requirements.txt` once the E2E run confirms nothing else imports them.
- [ ] Consider renaming this directory to `langgraph-postgres-checkpointer` — the name is now historical.
- [ ] Confirm `DIRECT_URL` is set in the deployment environment, not just locally. The pooled URL will appear to work and then fail intermittently under concurrency.
