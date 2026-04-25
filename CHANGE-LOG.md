## [0.1.0] - 2026-04-25
### Added
- Core database schema (7 tables) using SQLAlchemy 2.0 and Alembic for Supabase Postgres.
- Configured separate pooled (DATABASE_URL) and migration (DIRECT_URL) connections; migrations must use DIRECT_URL to bypass pgbouncer DDL restrictions.
