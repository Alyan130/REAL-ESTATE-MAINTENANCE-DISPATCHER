"""
app/api/v1/vendors.py

Vendor read and deactivate routes for property managers. Vendor *creation* lives
on the auth router with the other invite endpoints.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, status

from app.dependencies import PMUserDep, VendorServiceDep
from app.schemas.vendors import VendorResponse

router = APIRouter(prefix="/vendors", tags=["vendors"])


@router.get("/", response_model=list[VendorResponse])
def list_vendors(pm: PMUserDep, service: VendorServiceDep) -> list[VendorResponse]:
    """List all active vendors managed by the authenticated PM."""
    return service.list_for_pm(pm.id)


@router.get("/{vendor_id}", response_model=VendorResponse)
def get_vendor(
    vendor_id: uuid.UUID,
    pm: PMUserDep,
    service: VendorServiceDep,
) -> VendorResponse:
    """Get a single vendor by ID (must belong to the authenticated PM)."""
    return service.get_for_pm(vendor_id, pm.id)


@router.delete("/{vendor_id}", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_vendor(
    vendor_id: uuid.UUID,
    pm: PMUserDep,
    service: VendorServiceDep,
) -> None:
    """Remove the vendor from AI selection and disable their login."""
    service.deactivate(vendor_id, pm.id)
