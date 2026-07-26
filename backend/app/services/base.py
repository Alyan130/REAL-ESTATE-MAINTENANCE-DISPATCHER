"""
app/services/base.py

Shared service plumbing.

Services own the transaction boundary: repositories stage work, and exactly one
service call decides whether it lands. Nothing here imports FastAPI — a service
raises `AppError` subclasses and knows nothing about HTTP.
"""
from __future__ import annotations

from sqlalchemy.orm import Session


class BaseService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def _commit(self) -> None:
        """Commit, rolling back so the session is reusable if the write fails."""
        try:
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise
