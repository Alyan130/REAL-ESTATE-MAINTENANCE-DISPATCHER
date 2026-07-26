"""app/repositories/property_repo.py"""
from __future__ import annotations

import uuid

from app.models.property import Property
from app.repositories.base import BaseRepository


class PropertyRepository(BaseRepository[Property]):
    model = Property

    def list_active_for_pm(self, pm_id: uuid.UUID) -> list[Property]:
        return (
            self.db.query(Property)
            .filter(Property.pm_id == pm_id, Property.is_active.is_(True))
            .order_by(Property.created_at.desc())
            .all()
        )

    def list_active_ids_for_pm(self, pm_id: uuid.UUID) -> list[uuid.UUID]:
        """Ids only — used to scope a PM's ticket query to their properties."""
        return [
            row[0]
            for row in self.db.query(Property.id).filter(Property.pm_id == pm_id).all()
        ]

    def get_owned(self, property_id: uuid.UUID, pm_id: uuid.UUID) -> Property | None:
        """Active property belonging to this PM, or None. Ownership is the filter."""
        prop = self.get(property_id)
        if prop is None or prop.pm_id != pm_id or not prop.is_active:
            return None
        return prop

    def soft_delete(self, prop: Property) -> None:
        """Tickets and tenants survive — only the property leaves the PM's list."""
        prop.is_active = False
