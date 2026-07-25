"""
api/routes/tenants.py

Tenant read and deactivate routes for property managers.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException, status
from sqlalchemy.orm import joinedload

from api.deps import DbDep, PMUserDep
from models.property import Property
from models.tenant import Tenant
from schemas.tenants import TenantResponse

router = APIRouter(prefix="/tenants", tags=["tenants"])


# ─── Endpoints ───────────────────────────────────────────────────────────────


@router.get("/", response_model=list[TenantResponse])
def list_tenants(
    pm: PMUserDep,
    db: DbDep,
    property_id: uuid.UUID | None = None,
) -> list[TenantResponse]:
    """List tenants across properties managed by the authenticated PM, with optional property filter."""
    try:
        query = (
            db.query(Tenant)
            .join(Property, Tenant.property_id == Property.id)
            .filter(Property.pm_id == pm.id, Tenant.is_active.is_(True))
            .options(joinedload(Tenant.user))
        )

        if property_id is not None:
            query = query.filter(Tenant.property_id == property_id)

        tenants = query.all()

        return [
            TenantResponse(
                id=t.id,
                user_id=t.user_id,
                email=t.user.email,
                name=t.user.full_name,
                property_id=t.property_id,
                unit_number=t.unit_number,
                lease_start=t.lease_start,
                lease_end=t.lease_end,
                invite_status=t.user.invite_status,
                is_active=t.is_active,
            )
            for t in tenants
        ]
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list tenants: {exc}",
        )


@router.get("/{tenant_id}", response_model=TenantResponse)
def get_tenant(
    tenant_id: uuid.UUID,
    pm: PMUserDep,
    db: DbDep,
) -> TenantResponse:
    """Get a single tenant by ID (must belong to a property managed by the authenticated PM)."""
    try:
        tenant: Tenant | None = (
            db.query(Tenant)
            .join(Property, Tenant.property_id == Property.id)
            .options(joinedload(Tenant.user))
            .filter(
                Tenant.id == tenant_id,
                Property.pm_id == pm.id,
                Tenant.is_active.is_(True),
            )
            .first()
        )
        if tenant is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tenant not found.",
            )

        return TenantResponse(
            id=tenant.id,
            user_id=tenant.user_id,
            email=tenant.user.email,
            name=tenant.user.full_name,
            property_id=tenant.property_id,
            unit_number=tenant.unit_number,
            lease_start=tenant.lease_start,
            lease_end=tenant.lease_end,
            invite_status=tenant.user.invite_status,
            is_active=tenant.is_active,
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get tenant: {exc}",
        )


@router.delete("/{tenant_id}", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_tenant(
    tenant_id: uuid.UUID,
    pm: PMUserDep,
    db: DbDep,
) -> None:
    """Deactivate a tenant (set is_active=False on both the tenant profile and user)."""
    try:
        tenant: Tenant | None = (
            db.query(Tenant)
            .join(Property, Tenant.property_id == Property.id)
            .options(joinedload(Tenant.user))
            .filter(
                Tenant.id == tenant_id,
                Property.pm_id == pm.id,
                Tenant.is_active.is_(True),
            )
            .first()
        )
        if tenant is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tenant not found.",
            )

        tenant.is_active = False
        if tenant.user:
            tenant.user.is_active = False
        db.commit()
    except HTTPException:
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to deactivate tenant: {exc}",
        )
