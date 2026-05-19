## [0.9.0] - 2026-05-19
### Added
- `TicketState` refactored from `TypedDict` to a strict Pydantic `BaseModel` with proper LangGraph reducers (`Annotated[list, operator.add]`) on `vendors_contacted`, `negotiation_messages`, and `dispatch_attempts` — prevents list overwrites in multi-step agent loops.
- Implemented `get_checkpointer()` context manager in `backend/agentic_AI/checkpointer.py` using `RedisSaver` from `langgraph-checkpoint-redis`; connects to Upstash over TCP (`rediss://`) with SSL auto-enabled.
### Changed
- Replaced REST-based Upstash vars (`UPSTASH_REDIS_REST_URL`, `UPSTASH_REDIS_REST_TOKEN`) in `.env` and `config.py` with a single `REDIS_URL` TCP connection string — REST client is no longer needed.
- Synced `config.py` `Settings` class with all `.env` vars: added `LANGSMITH_*`, `REDIS_URL`, and `OPENAI_API_KEY` fields.

## [0.8.0] - 2026-05-16

### Added
- Scaffolded `agentic_AI` directory structure in `backend/` including empty components for agents, nodes, and tools.
- Set up foundational modules (`ticket_state.py`, `redis_checkpointer.py`) to prepare for LangGraph integration.

## [0.7.0] - 2026-05-13
### Changed
- Centralized all Pydantic models into `backend/schemas/` to improve code organization and maintainability.
- Updated all API routes to import from the new unified schema package.
- Standardized `TenantResponse` and `VendorResponse` variants to eliminate duplication across routes.

## [0.6.0] - 2026-04-26
### Added
- Maintenance ticket submission system with multi-photo support; uses `BackgroundTasks` for non-blocking uploads to Supabase Storage.
- `backend/core/storage.py` helper for Supabase Storage uploads; returns public URLs for persistent media access.
- Role-based ticket listing and retrieval; PMs see property-scoped tickets, Tenants see only their own.
- Status update endpoint for PMs to transition tickets through the maintenance workflow.
- `backend/.env` with production-ready credentials for Supabase, Resend, and PostgreSQL.

### Changed
- Centralized all configurations in `Settings` class; `database.py` and other modules now use `core.config.settings` for consistency.
- Standardized `DATABASE_URL` and `DIRECT_URL` handling to support Supabase connection pooling across the app.

## [0.5.0] - 2026-04-26
### Changed
- Split `pm.py` into dedicated `properties.py`, `tenants.py`, and `vendors.py` routers — each resource now has its own file and URL prefix.
- Moved tenant/vendor invite creation and resend endpoints into `auth.py` under `/auth/invites/*` to centralize all invite logic.
- Deleted `pm.py` and updated `main.py` to register the four new routers.

### Added
- Full CRUD for properties: create, list, get by ID, and soft-delete — all scoped to the authenticated PM.
- Read and deactivate endpoints for tenants and vendors — deactivation disables both the profile and the linked user account.
- Tenants list supports optional `property_id` query filter.

## [0.4.0] - 2026-04-25
### Added
- Invite acceptance (`POST /auth/accept-invite`) to set initial password and return a login token.
- PM invite resend endpoints; `users.last_invite_iat` invalidates older invite tokens (new Alembic migration).


## [0.3.0] - 2026-04-25
### Added
- `backend/core/email.py` — Resend-powered email service with `send_invite_email()`. Sends HTML invite emails with a CTA link to `{BASE_URL}/accept-invite?token={token}`. Uses `onboarding@resend.dev` as the sender for development — swap to a verified domain before production.
- `backend/api/routes/pm.py` — PM-only router with four endpoints: `POST /pm/tenants` (create tenant + User record + invite email), `POST /pm/vendors` (create vendor + User record + invite email), `GET /pm/tenants` (list tenants across PM's properties with invite status), `GET /pm/vendors` (list PM's vendors with invite status). All endpoints gated by `require_pm`.
- `backend/api/deps.py` — added `require_pm` dependency and `PMUserDep` type alias. Returns 403 if authenticated user's role is not `"pm"`.
- `backend/core/config.py` — added `RESEND_API_KEY` and `BASE_URL` settings. `BASE_URL` defaults to `https://resend.dev` for development.
- `backend/requirements.txt` — added `resend` SDK.
- `backend/main.py` — registered the `/pm` router.


## [0.2.0] - 2026-04-25
### Added
- Implemented core authentication infrastructure including bcrypt password hashing, JWT token management, and auth middleware.
- Created `POST /auth/login` endpoint with validation for active status and approved invite status.
- Added comprehensive test suite for authentication utilities and session management.

## [0.1.0] - 2026-04-25
### Added
- Core database schema (7 tables) using SQLAlchemy 2.0 and Alembic for Supabase Postgres.
- Configured separate pooled (DATABASE_URL) and migration (DIRECT_URL) connections; migrations must use DIRECT_URL to bypass pgbouncer DDL restrictions.

