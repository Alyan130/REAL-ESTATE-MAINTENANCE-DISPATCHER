"""
app/api/v1/tenants.py

Tenant read and deactivate routes for property managers. Tenant *creation* lives
on the auth router with the other invite endpoints.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, status

from app.dependencies import PMUserDep, TenantServiceDep
from app.schemas.tenants import TenantResponse

router = APIRouter(prefix="/tenants", tags=["tenants"])


@router.get("/", response_model=list[TenantResponse])
def list_tenants(
    pm: PMUserDep,
    service: TenantServiceDep,
    property_id: uuid.UUID | None = None,
) -> list[TenantResponse]:
    """List tenants across the PM's properties, optionally filtered to one."""
    return service.list_for_pm(pm.id, property_id)


@router.get("/{tenant_id}", response_model=TenantResponse)
def get_tenant(
    tenant_id: uuid.UUID,
    pm: PMUserDep,
    service: TenantServiceDep,
) -> TenantResponse:
    """Get a single tenant (must belong to a property this PM manages)."""
    return service.get_for_pm(tenant_id, pm.id)


@router.delete("/{tenant_id}", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_tenant(
    tenant_id: uuid.UUID,
    pm: PMUserDep,
    service: TenantServiceDep,
) -> None:
    """Deactivate the tenant profile and their login together."""
    service.deactivate(tenant_id, pm.id)
