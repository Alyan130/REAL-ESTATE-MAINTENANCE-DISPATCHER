"""
app/services/property_service.py

Properties are the top of the hierarchy — tenants and tickets both hang off one.
"""
from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.exceptions import NotFoundError
from app.models.property import Property
from app.repositories.property_repo import PropertyRepository
from app.schemas.properties import CreatePropertyRequest, PropertyResponse
from app.services.base import BaseService


class PropertyService(BaseService):
    def __init__(self, db: Session) -> None:
        super().__init__(db)
        self.properties = PropertyRepository(db)

    def create(self, pm_id: uuid.UUID, data: CreatePropertyRequest) -> PropertyResponse:
        prop = self.properties.add(
            Property(pm_id=pm_id, name=data.name, address=data.address)
        )
        self._commit()
        self.db.refresh(prop)
        return PropertyResponse.model_validate(prop)

    def list_for_pm(self, pm_id: uuid.UUID) -> list[PropertyResponse]:
        return [
            PropertyResponse.model_validate(prop)
            for prop in self.properties.list_active_for_pm(pm_id)
        ]

    def get_for_pm(self, property_id: uuid.UUID, pm_id: uuid.UUID) -> PropertyResponse:
        return PropertyResponse.model_validate(self._owned_or_404(property_id, pm_id))

    def delete(self, property_id: uuid.UUID, pm_id: uuid.UUID) -> None:
        """
        Soft delete. The property leaves the PM's list while its tickets and
        tenant records stay in the database.
        """
        self.properties.soft_delete(self._owned_or_404(property_id, pm_id))
        self._commit()

    def _owned_or_404(self, property_id: uuid.UUID, pm_id: uuid.UUID) -> Property:
        """
        Someone else's property is reported as missing, not forbidden — a 403
        would confirm that the id exists.
        """
        prop = self.properties.get_owned(property_id, pm_id)
        if prop is None:
            raise NotFoundError("Property not found.")
        return prop
