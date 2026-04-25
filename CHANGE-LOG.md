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

