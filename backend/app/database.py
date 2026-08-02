from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings

# Query params that Supabase puts in the connection string for Prisma's benefit
# and that psycopg2 rejects outright ("invalid dsn: invalid connection option").
# Supabase's dashboard hands out a pooler URL carrying `?pgbouncer=true`, so
# pasting it verbatim — the obvious thing to do — makes every connection fail
# before it is attempted. Stripping it here means the documented URL just works.
_NON_LIBPQ_PARAMS = {"pgbouncer", "schema", "connection_limit", "pool_timeout"}


def normalise_dsn(url: str) -> str:
    """Drop ORM-specific query params libpq doesn't understand."""
    parsed = urlparse(url)
    if not parsed.query:
        return url

    kept = [
        (key, value)
        for key, value in parse_qsl(parsed.query, keep_blank_values=True)
        if key.lower() not in _NON_LIBPQ_PARAMS
    ]
    return urlunparse(parsed._replace(query=urlencode(kept)))


engine = create_engine(
    normalise_dsn(settings.DATABASE_URL),
    # Transaction-pooling poolers do not support server-side prepared statements
    # or session-level state, so nothing here may assume a sticky session.
    connect_args={"options": "-c statement_timeout=10000"},
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """FastAPI dependency — yields a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
