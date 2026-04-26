# Implement Supabase Database Schema via SQLAlchemy and Alembic

This plan outlines the steps to build the requested database schema in the `backend/` directory using SQLAlchemy as the ORM, and configure Alembic for database migrations targeted at the Supabase PostgreSQL database.

## Proposed Changes

### Configuration and Initial Setup
#### [NEW] `backend/requirements.txt`
List of python dependencies needed (SQLAlchemy, alembic, psycopg2-binary, python-dotenv).

#### [NEW] `backend/.env`
Define `DATABASE_URL` (pgbouncer/pooler) and `DIRECT_URL` (direct/migrations) with the provided credentials.

### Migrations Setup (Alembic)
#### [NEW] `backend/alembic.ini`
Alembic config.
#### [NEW] `backend/alembic/env.py`
To configure the direct connection using `os.getenv("DIRECT_URL")` and to point to the base metadata of the models.

### ORM Details
#### [NEW] `backend/models/*.py` (or `backend/models.py`)
Implement the tables mapping the exact fields requested:
- `users`: ID maps to `uuid` and sets the Supabase Auth id relation mentally.
- `properties`: `pm_id` -> users.
- `tenants`: `user_id` -> users, `property_id` -> properties.
- `vendors`: `pm_id` -> users, uses PostgreSQL ARRAY type for `categories`.
- `tickets`: `property_id` -> properties, `tenant_id` -> tenants. Uses default 'OPEN'.
- `vendor_jobs`: `ticket_id` -> tickets, `vendor_id` -> vendors.
- `notifications`: `user_id` -> users.

Uses `uuid.uuid4` for default generation where needed, and `sqlalchemy.sql.functions.now()` for `created_at` datetimes.

#### [NEW] `backend/database.py` (optional, for pooler)
Engine initialization using `DATABASE_URL` for future API logic.

## Verification Plan
### Automated Tests
- Run `cd backend && alembic revision --autogenerate -m "Initial schema"` to verify alembic tracks the models successfully against the database.
- Read alembic auto-generated output to verify no errors.

### Manual Verification
- Verify the generated schema in their Supabase portal (Table Editor).
