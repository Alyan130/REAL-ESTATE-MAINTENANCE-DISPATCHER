from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings

# Use connection_args for pgbouncer compatibility (no prepared statements)
engine = create_engine(
    settings.DATABASE_URL,
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
