# Changelog

## [0.2.0] - 2026-04-25
### Added
- `backend/core/security.py` — bcrypt password hashing (`hash_password`, `verify_password`) and JWT helpers (`create_token`, `decode_token`). Token lifetimes: `login` = 60 days, `invite` = 48 h, `reset` = 1 h. Signature/expiry errors are re-raised as specific `PyJWT` exceptions so callers can distinguish them.
- `backend/core/config.py` — `Settings` via `pydantic-settings`; reads `.env` by absolute path (works from any cwd). Keys: `JWT_SECRET_KEY`, `JWT_ALGORITHM`, `BCRYPT_WORK_FACTOR` (default 12). `JWT_SECRET_KEY` must be overridden in production.
- `backend/api/routes/auth.py` — `POST /auth/login`: returns a signed login JWT on success; `401` for bad creds or inactive account; `403` for `pending` invite status. Invite check runs before the active check — keep that order.
- `backend/api/deps.py` — `get_current_user` FastAPI dependency + `CurrentUserDep` type alias. Extracts Bearer token, decodes it, loads `User` from DB — raises `401` on any failure. Use `CurrentUserDep` in route handlers to protect routes.
- `backend/main.py` — FastAPI app entry point; registers the `/auth` router.
- `backend/requirements.txt` — added `fastapi[standard]`, `pydantic-settings`, `bcrypt`, `PyJWT`, `pytest`, `httpx`.
- `backend/tests/__init__.py` — package init for the test suite.
- `docs/features/authentication-phase-1/` — feature plan, task list, and architecture diagram for this phase.

## [0.1.0] - 2026-04-25
### Added
- Database schema and Alembic migrations for all seven core tables: `users`, `properties`, `tenants`, `vendors`, `tickets`, `vendor_jobs`, `notifications`.
- SQLAlchemy models with full relationships targeting Supabase PostgreSQL (pgbouncer-compatible engine config).
