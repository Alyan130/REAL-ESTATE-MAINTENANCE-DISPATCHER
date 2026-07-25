## [0.14.0] - 2026-07-26

### Added
- **Frontend demo mode — TEMPORARY, delete once a real database is reachable.** Lets the UI be reviewed with no backend at all. Enabled by `NEXT_PUBLIC_DEMO_MODE=true` in `frontend/.env.local`.
  - `frontend/src/lib/demo/fixtures.ts` — the dataset: 3 properties, 3 tenants (one with a pending invite), 4 vendors, 8 tickets covering `PENDING_APPROVAL`, `DISPATCHED`, `NEEDS_ATTENTION`, `ERROR`, `TRIAGED`, and `CANCELLED`. Structural, pest, and appliance are deliberately left uncovered so the vendors screen's coverage-gap warning has something real to report.
  - `frontend/src/lib/demo/demo-store.ts` — mutable in-memory state plus simulated background work: photo upload and classification resolve after ~4.5s, approval-to-dispatch after ~5s, and a category with no vendor settles on `NEEDS_ATTENTION` exactly as the real dispatch agent would.
  - `frontend/src/lib/demo/demo-adapter.ts` — an axios adapter covering all 22 endpoints.
  - `frontend/src/components/demo/demo-notice.tsx` — a persistent "Demo data — no backend" badge, a credential picker on the login screen, and links that exercise each accept-invite error state.
- **Why it plugs in at the transport layer:** the only change outside `lib/demo/` is one `if` in `lib/api-client.ts` swapping `apiClient.defaults.adapter`. No screen, component, or store knows demo mode exists, so the code paths exercised in review are the same ones that will talk to FastAPI. The adapter returns the real `{error, code}` envelope and real status codes (`409 TICKET_NOT_AWAITING_APPROVAL`, `400 DUPLICATE_EMAIL`, …), so the UI's error branches genuinely fire.
- Demo logins, all with password `demo1234`: `pm@demo.test`, `tenant@demo.test`, `vendor@demo.test`. `sofia@demo.test` reproduces `ACCOUNT_PENDING` and `disabled@demo.test` reproduces `ACCOUNT_DISABLED`. On `/accept-invite`, the tokens `expired`, `superseded`, `used`, and `bad` each trigger their matching error.

### Notes
- **Why this exists:** the Supabase project in `backend/.env` (`tybvutjzxolwgemagwfu`) is unreachable — both `DATABASE_URL` and `DIRECT_URL` answer `FATAL: (ENOTFOUND) tenant/user not found`, so it has been deleted, paused, or its credentials are stale. Nothing can log in until that is resolved.
- **Two blockers to clear before a real login works**, independent of the missing project:
  1. `DATABASE_URL` carries `?pgbouncer=true`, a Prisma-only flag. psycopg2 rejects it outright: `invalid dsn: invalid connection option "pgbouncer"`. Strip it, or drop the param when building the engine in `app/database.py`.
  2. **There is no way to create the first PM.** No signup endpoint exists, and both invite endpoints require an authenticated PM. The first account has to be inserted directly into the database — a seed script is still to be written.
- Demo state resets on page refresh. Photos are picsum placeholders. The fake JWT is structurally valid with a junk signature; nothing in the frontend verifies signatures, and it never reaches a real API.
- **To remove:** delete `frontend/src/lib/demo/`, delete `frontend/src/components/demo/`, remove the `IS_DEMO_MODE` block in `lib/api-client.ts`, drop the three `Demo*` imports in `app/layout.tsx` and `app/login/page.tsx`, and set `NEXT_PUBLIC_DEMO_MODE=false`.
- **Verification status:** `tsc`, `eslint --max-warnings=0`, and `next build` all pass, and the login page was confirmed to render the demo panel. The flows were *not* clicked through in a browser.

## [0.13.0] - 2026-07-26
### Changed
- **Backend restructured to `docs/rules/folder-structure.md`.** Everything moved under `backend/app/`: `core/config.py → app/config.py`, `database.py → app/database.py`, `api/deps.py → app/dependencies.py`, `main.py → app/main.py`, and `api/routes/*.py → app/api/v1/*.py`. `models/`, `schemas/`, `core/`, and `agentic_AI/` moved verbatim. Every root-relative import (`from core.config import ...`) is now absolute from the package (`from app.config import ...`).
- **Run command is now `uvicorn app.main:app`** (from `backend/`), not `uvicorn main:app`. `app/main.py` is a `create_app()` factory — wiring only — with `app = create_app()` at module scope.
- **URLs are unchanged.** v1 is mounted without a prefix via `app/api/router.py → app/api/v1/router.py`, so `/auth/login`, `/tickets`, `/properties/` etc. all still resolve. Versioning is a file-layout convention for now; pinning v1 to `/v1` later can keep the unprefixed mount as an alias.
- **Route handlers are thin.** All 22 endpoints now validate, call one service method, and return a schema. No handler contains a query, a commit, or a `try/except`.
- `alembic/` → `migrations/`; `script_location` updated in `alembic.ini`. Revision files moved untouched — no schema change and no new revision.
### Added
- **`app/services/`** — `auth`, `property`, `tenant`, `vendor`, `ticket`. Services own the transaction boundary and raise `AppError` subclasses; none of them import FastAPI. `ticket_service.py` also absorbs the six background helpers that were at module scope in `api/routes/tickets.py` (`process_ticket_submission`, `run_approval`, and the resume/fallback/escalate internals), which keep opening their own `SessionLocal()` because a request-scoped session is closed long before they finish.
- `app/services/invites.py::issue_invite()` — mint token, stamp `last_invite_iat`, send email. That sequence was duplicated in four places; the stamp is what retires older invite links, so having one copy matters.
- **`app/repositories/`** — generic `BaseRepository[ModelT]` plus one repo per aggregate. Repositories query and stage only; they never commit. The two joins that carry meaning are preserved intact: `Tenant → Property` for PM scoping with `joinedload(Tenant.user)`, and `Vendor → User` **on email** (there is no FK between them) to supply `invite_status`.
- **`app/exceptions.py`** — `AppError` hierarchy plus handlers for `AppError`, `HTTPException`, `RequestValidationError`, and unhandled `Exception`. All four now emit the envelope `docs/rules/error-handling.md` requires: `{"error": "...", "code": "..."}`. Codes: `INVALID_CREDENTIALS`, `ACCOUNT_PENDING`, `ACCOUNT_DISABLED`, `NOT_AUTHENTICATED`, `PASSWORD_MISMATCH`, `INVALID_TOKEN`, `INVITE_EXPIRED`, `INVITE_SUPERSEDED`, `INVITE_ALREADY_ACCEPTED`, `DUPLICATE_EMAIL`, `TICKET_NOT_AWAITING_APPROVAL`, `NOT_FOUND`, `FORBIDDEN`, `VALIDATION_ERROR`, `INTERNAL_ERROR`.
- `app/middleware.py` (CORS registration, moved out of `main.py`) and `app/core/logging.py` (`configure_logging()`; format and level only, and it pins `sqlalchemy.engine` to WARNING so statements and their parameters stay out of the logs).
- `require_tenant` dependency alongside `require_pm`, so the tenant-only guard on ticket creation is declared on the route instead of checked in the handler body.
### Fixed
- **`agentic_AI/nodes/intake/` was shadowing `nodes/intake.py`.** An empty package (a docstring, nothing else) sat next to the real module, and a directory wins during import resolution — so `from agentic_AI.nodes.intake import classify_node` raised ImportError and the whole intake graph was unreachable. It was invisible because the graph only runs inside background tasks, whose failures are swallowed into `status = "ERROR"`. The empty package is deleted; `intake_graph` now imports.
- `orchestration_agent.py` imported `CompiledGraph` from `langgraph.graph.graph`, which langgraph 1.x removed — importing the module raised `ModuleNotFoundError`, breaking approve/dispatch at runtime. Switched to `CompiledStateGraph` from `langgraph.graph.state`.
- 500 responses no longer leak internals. Several handlers interpolated the caught exception into `detail` (`f"Failed to create tenant: {exc}"`); the unhandled-exception handler now logs the traceback and returns a fixed sentence.
- A missing `Authorization` header returns 401 `NOT_AUTHENTICATED` instead of `HTTPBearer`'s bare 403 (`auto_error=False`).
- An invite token whose `sub` is not a UUID now returns 400 `INVALID_TOKEN` instead of surfacing a database error as a 500.
### Frontend
- `src/lib/errors.ts` reads the `{error, code}` envelope and exposes `code` on `ApiError`, falling back to FastAPI's `{detail}` shape (string and 422 list forms) for anything that answers before the handlers.
- Login, accept-invite, and both invite modals branch on `code` rather than regex-matching message text, so copy changes on either side can no longer break a UI branch. Status-code fallbacks are retained.
### Notes
- Behaviour is otherwise unchanged, including two deliberate carry-overs: a ticket submitted with no photos stays `OPEN` and never runs the graph (so it is never classified), and ticket ownership checks do not test `Property.is_active`, which keeps a soft-deleted property's ticket history reachable.
- `tests/` still holds only an empty `__init__.py`. No suite was ported or invented as part of a move.

## [0.12.0] - 2026-07-26
### Added
- **Next.js 16 frontend** (`frontend/`) — TypeScript, Tailwind v4, Zustand, Axios, Motion, Lucide. Covers every Section-A screen in `docs/context/screens.md`: login, accept-invite, PM dashboard, PM ticket detail, properties list/detail, tenants, vendors, tenant ticket list/submit/detail.
- `src/lib/api/*` — one typed module per domain (`auth`, `properties`, `tenants`, `vendors`, `tickets`), mirroring `backend/schemas/` exactly. Paths keep the backend's literal trailing slashes (`/properties/` vs `/tickets`) so no request eats a 307 redirect.
- `src/lib/api-client.ts` — single axios instance; bearer token injected from module scope (pushed by the auth store, so the dependency stays one-directional), plus a 401 handler that signs out and bounces to login. `/auth/login` and `/auth/accept-invite` are exempt — a 401 there is an expected answer, not a dead session.
- `src/lib/errors.ts` — FastAPI `detail` (string *and* 422 issue-list shapes) normalised to one plain-English sentence. 5xx detail is never surfaced verbatim, since several backend handlers interpolate the exception into the message.
- `src/lib/jwt.ts` — unverified claim decode to read `role`/`sub`. There is no `/auth/me`, so the token is the only source of the user's role; verification stays server-side.
- `src/lib/use-async.ts` — `useAsync` (superseded responses discarded, so a fast filter change can't be overwritten by a slower earlier one) and `usePolling` (bounded interval). `PENDING_UPLOAD` and `DISPATCHING` both resolve in a background task with no push channel, so the affected screens poll and stop.
- `src/lib/status.ts` — separate PM and tenant status vocabularies. `tenantStatusLabel` maps `ERROR` and `NEEDS_ATTENTION` to "your property manager is reviewing this"; `TenantStatusBadge` is a distinct component from `StatusBadge` so internal vocabulary can't leak into a tenant screen by accident.
- Vendor **coverage-gap detection** on the vendors screen — any of the seven vendor categories with no active vendor is named explicitly, turning a silent `NEEDS_ATTENTION` escalation into a fixable setup step.
- `/vendor` landing page — vendors have zero backend endpoints (Section B), so an accepted invite lands on an honest explanation rather than a dead route.
### Changed
- `main.py` — added `CORSMiddleware`. Without it the browser blocked every request before it reached a route, so the API was unreachable from any frontend.
- `core/config.py` — new `CORS_ORIGINS` setting (comma-separated) with a `cors_origins_list` property. Allow-listed, never `"*"`: a wildcard would let any site call the API with a user's bearer token.
- `.env.example` was empty and is now populated with every backend and frontend variable, per the security rules.
### Notes
- **`BASE_URL` in `backend/.env` must point at the frontend origin.** `send_invite_email` builds `{BASE_URL}/accept-invite?token=...`; it is currently `https://maintainence.com`, so local invite links resolve to a domain that isn't running the app.
- Two deliberate deviations from `design.md`'s palette, required by that doc's own 80% saturation cap: Verde Elétrico `#00FF00` → `#2e9e63` and Laranja `#FFA500` → `#cc8433`. Pure black is likewise replaced by a charcoal.
- The bearer token is held in `localStorage` via Zustand `persist`. The backend exposes no cookie or refresh flow, so this is the only option available today; moving to an httpOnly cookie is a backend change.
- Tenant detail deliberately withholds `ai_summary`, `priority`, and vendor data — the endpoint returns them, and the frontend drops them on purpose.

## [0.11.0] - 2026-07-13
### Changed
- **PM approval is now native LangGraph human-in-the-loop.** The orchestration graph pauses at a new `human_approval_node` via `interrupt()` (state persisted to the Redis checkpointer on thread `ticket-{id}`) instead of ending at `notify_pm`. `POST /tickets/{id}/approve` **resumes the same graph** with `Command(resume={"approved": True})` — the paused state (incl. `category`) is preserved, removing the DB-rehydration step on the happy path.
- `agentic_AI/agents/orchestration_agent.py` — added `human_approval_node`, `route_on_decision`, and `cancel_node`; rewired `notify_pm → human_approval → dispatch | cancel`. P1 path unchanged.
- `agentic_AI/checkpointer.py` — `RedisSaver` now configured with a **3-day TTL** (`CHECKPOINT_TTL`, `refresh_on_read=True`) so paused approval workflows survive until the PM acts.
- `api/routes/tickets.py` — replaced the fresh-invocation `_run_dispatch` with `_run_approval`: resume via `_resume_approval_graph` (detects a live interrupt through `graph.aget_state(...).next`), **DB-fallback** to `dispatch_graph` if the checkpoint was evicted, and `NEEDS_ATTENTION` escalation on unrecoverable failure. `/approve` and `/reject` now guard `status == PENDING_APPROVAL` (409 otherwise); `/reject` writes `CANCELLED` synchronously rather than through the graph.
### Notes
- Reject deliberately bypasses the graph — a terminal state-set must not depend on a live checkpoint; the paused graph expires via TTL and the guard makes it unresumable.
- Durability tradeoff: a paused workflow lives in Redis; the DB-fallback + 3-day TTL are the mitigation for checkpoint loss.

## [0.10.0] - 2026-07-13
### Added
- **Dispatch agent** (`agentic_AI/agents/dispatch_agent.py`) — a LangGraph subgraph: `select_vendor → dispatch_job | escalate_to_pm`. Selects the single best-matching vendor for an approved/P1 ticket, creates a `PENDING` `VendorJob`, and emails the vendor a job offer; escalates to the PM when no vendor is available.
- `agentic_AI/tools/dispatch.py` — `find_best_vendor()` (deterministic filter by pm/category/active/capacity, ranked by rating) and `create_vendor_job()`. Vendor exclusion for "already contacted" is driven by the `VendorJob` table (authoritative across the separate P1 and PM-approval graph invocations), not by graph reducer state.
- `agentic_AI/nodes/dispatch.py` — `select_vendor_node`, `route_after_selection`, `dispatch_job_node`, `escalate_to_pm_node`, following the intake node convention (per-node `SessionLocal`, errors surfaced as `{"error": ...}` state).
- `core/categories.py` — shared `TicketCategory`/`VendorCategory` `Literal` vocabulary so intake output and vendor input cannot drift. `"other"` is a ticket-only catch-all, excluded from vendor categories.
- `core/email.py::send_job_offer_email()` — Resend sender for vendor job offers, modeled on `send_invite_email` (sync, fire-and-forget).
- `POST /tickets/{id}/approve` and `POST /tickets/{id}/reject` in `api/routes/tickets.py`. Approve triggers dispatch in the background via `_run_dispatch`, which rebuilds `TicketState` from the DB (hydrating `category`, required for vendor matching). Reject → `CANCELLED`.
### Changed
- `agentic_AI/agents/orchestration_agent.py` — replaced the `trigger_dispatch_node` placeholder with the real `dispatch_graph` embedded as a subgraph node.
- `agentic_AI/output_schemas.py` — `IntakeClassification.category` constrained to `TicketCategory`.
- `schemas/vendors.py` — `CreateVendorRequest.categories` constrained to `list[VendorCategory]` (off-vocabulary categories now rejected with 422; no DB migration — column stays `ARRAY(String)`).
### Notes
- Retry-on-decline (contact the next vendor when one declines) is deferred to the Negotiation agent; the DB-based exclusion and escalation that support it are in place. `VendorJob` `DECLINED`/`QUOTED` transitions land with negotiation and need no migration (`status` is free `String(20)`).

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

