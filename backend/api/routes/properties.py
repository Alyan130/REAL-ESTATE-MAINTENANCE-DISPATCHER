"""
api/routes/properties.py

Property CRUD routes for property managers.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from api.deps import DbDep, PMUserDep
from models.property import Property

router = APIRouter(prefix="/properties", tags=["properties"])


# ─── Schemas ──────────────────────────────────────────────────────────────────


class CreatePropertyRequest(BaseModel):
    name: str
    address: str


class PropertyResponse(BaseModel):
    id: uuid.UUID
    pm_id: uuid.UUID
    name: str
    address: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ─── Endpoints ───────────────────────────────────────────────────────────────


@router.post("/", response_model=PropertyResponse, status_code=status.HTTP_201_CREATED)
def create_property(
    body: CreatePropertyRequest,
    pm: PMUserDep,
    db: DbDep,
) -> PropertyResponse:
    """Create a new property owned by the authenticated PM."""
    try:
        prop = Property(
            pm_id=pm.id,
            name=body.name,
            address=body.address,
        )
        db.add(prop)
        db.commit()
        db.refresh(prop)

        return PropertyResponse.model_validate(prop)
    except HTTPException:
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create property: {exc}",
        )


@router.get("/", response_model=list[PropertyResponse])
def list_properties(
    pm: PMUserDep,
    db: DbDep,
) -> list[PropertyResponse]:
    """List all active properties for the authenticated PM."""
    try:
        properties = (
            db.query(Property)
            .filter(Property.pm_id == pm.id, Property.is_active.is_(True))
            .order_by(Property.created_at.desc())
            .all()
        )
        return [PropertyResponse.model_validate(p) for p in properties]
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list properties: {exc}",
        )


@router.get("/{property_id}", response_model=PropertyResponse)
def get_property(
    property_id: uuid.UUID,
    pm: PMUserDep,
    db: DbDep,
) -> PropertyResponse:
    """Get a single property by ID (must belong to the authenticated PM)."""
    try:
        prop: Property | None = db.get(Property, property_id)
        if prop is None or prop.pm_id != pm.id or not prop.is_active:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Property not found.",
            )
        return PropertyResponse.model_validate(prop)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get property: {exc}",
        )


@router.delete("/{property_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_property(
    property_id: uuid.UUID,
    pm: PMUserDep,
    db: DbDep,
) -> None:
    """Soft-delete a property (set is_active=False)."""
    try:
        prop: Property | None = db.get(Property, property_id)
        if prop is None or prop.pm_id != pm.id or not prop.is_active:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Property not found.",
            )

        prop.is_active = False
        db.commit()
    except HTTPException:
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete property: {exc}",
        )
