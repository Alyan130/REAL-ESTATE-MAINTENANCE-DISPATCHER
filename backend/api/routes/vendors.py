"""
api/routes/vendors.py

Vendor read and deactivate routes for property managers.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException, status

from api.deps import DbDep, PMUserDep
from models.user import User
from models.vendor import Vendor
from schemas.vendors import VendorResponse

router = APIRouter(prefix="/vendors", tags=["vendors"])


# ─── Endpoints ───────────────────────────────────────────────────────────────


@router.get("/", response_model=list[VendorResponse])
def list_vendors(
    pm: PMUserDep,
    db: DbDep,
) -> list[VendorResponse]:
    """List all active vendors managed by the authenticated PM."""
    try:
        results = (
            db.query(Vendor, User)
            .join(User, Vendor.email == User.email)
            .filter(Vendor.pm_id == pm.id, Vendor.is_active.is_(True))
            .all()
        )

        return [
            VendorResponse(
                id=v.id,
                name=v.name,
                email=v.email,
                phone=v.phone,
                categories=v.categories,
                max_concurrent_jobs=v.max_concurrent_jobs,
                rating=float(v.rating),
                invite_status=u.invite_status,
                is_active=v.is_active,
            )
            for v, u in results
        ]
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list vendors: {exc}",
        )


@router.get("/{vendor_id}", response_model=VendorResponse)
def get_vendor(
    vendor_id: uuid.UUID,
    pm: PMUserDep,
    db: DbDep,
) -> VendorResponse:
    """Get a single vendor by ID (must belong to the authenticated PM)."""
    try:
        result = (
            db.query(Vendor, User)
            .join(User, Vendor.email == User.email)
            .filter(
                Vendor.id == vendor_id,
                Vendor.pm_id == pm.id,
                Vendor.is_active.is_(True),
            )
            .first()
        )
        if result is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Vendor not found.",
            )

        v, u = result
        return VendorResponse(
            id=v.id,
            name=v.name,
            email=v.email,
            phone=v.phone,
            categories=v.categories,
            max_concurrent_jobs=v.max_concurrent_jobs,
            rating=float(v.rating),
            invite_status=u.invite_status,
            is_active=v.is_active,
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get vendor: {exc}",
        )


@router.delete("/{vendor_id}", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_vendor(
    vendor_id: uuid.UUID,
    pm: PMUserDep,
    db: DbDep,
) -> None:
    """Deactivate a vendor (set is_active=False on both the vendor record and user)."""
    try:
        vendor: Vendor | None = (
            db.query(Vendor)
            .filter(
                Vendor.id == vendor_id,
                Vendor.pm_id == pm.id,
                Vendor.is_active.is_(True),
            )
            .first()
        )
        if vendor is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Vendor not found.",
            )

        vendor.is_active = False

        if vendor.email:
            user: User | None = db.query(User).filter(User.email == vendor.email).first()
            if user:
                user.is_active = False

        db.commit()
    except HTTPException:
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to deactivate vendor: {exc}",
        )
