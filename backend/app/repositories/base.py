"""
app/repositories/base.py

Generic persistence helper.

Repositories query and stage work; they never commit and never raise HTTP
errors. The service that calls them owns the transaction, so a single service
method can span several repositories and still commit or roll back as one unit.
"""
from __future__ import annotations

import uuid
from typing import Generic, TypeVar

from sqlalchemy.orm import Session

from app.models.base import Base

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    """Subclasses set `model` to their SQLAlchemy class."""

    model: type[ModelT]

    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self, entity_id: uuid.UUID) -> ModelT | None:
        return self.db.get(self.model, entity_id)

    def add(self, entity: ModelT) -> ModelT:
        """Stage an insert. Call `flush()` when the generated id is needed."""
        self.db.add(entity)
        return entity

    def flush(self) -> None:
        """Send pending SQL without ending the transaction."""
        self.db.flush()

    def refresh(self, entity: ModelT) -> ModelT:
        self.db.refresh(entity)
        return entity
