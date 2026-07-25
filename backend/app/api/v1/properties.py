"""
app/api/v1/properties.py

Property CRUD for property managers.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, status

from app.dependencies import PMUserDep, PropertyServiceDep
from app.schemas.properties import CreatePropertyRequest, PropertyResponse

router = APIRouter(prefix="/properties", tags=["properties"])


@router.post("/", response_model=PropertyResponse, status_code=status.HTTP_201_CREATED)
def create_property(
    body: CreatePropertyRequest,
    pm: PMUserDep,
    service: PropertyServiceDep,
) -> PropertyResponse:
    """Create a new property owned by the authenticated PM."""
    return service.create(pm_id=pm.id, data=body)


@router.get("/", response_model=list[PropertyResponse])
def list_properties(pm: PMUserDep, service: PropertyServiceDep) -> list[PropertyResponse]:
    """List all active properties for the authenticated PM."""
    return service.list_for_pm(pm.id)


@router.get("/{property_id}", response_model=PropertyResponse)
def get_property(
    property_id: uuid.UUID,
    pm: PMUserDep,
    service: PropertyServiceDep,
) -> PropertyResponse:
    """Get a single property by ID (must belong to the authenticated PM)."""
    return service.get_for_pm(property_id, pm.id)


@router.delete("/{property_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_property(
    property_id: uuid.UUID,
    pm: PMUserDep,
    service: PropertyServiceDep,
) -> None:
    """Soft-delete a property. Its tickets and tenants are retained."""
    service.delete(property_id, pm.id)
