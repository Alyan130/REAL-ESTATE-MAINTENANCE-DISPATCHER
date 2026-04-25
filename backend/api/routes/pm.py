"""
api/routes/pm.py

Property Manager routes — tenant/vendor creation and listing.
"""
from __future__ import annotations

import uuid
from datetime import date

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import joinedload

from api.deps import DbDep, PMUserDep
from core.email import send_invite_email
from core.security import create_token
from models.property import Property
from models.tenant import Tenant
from models.user import User
from models.vendor import Vendor

router = APIRouter(prefix="/pm", tags=["pm"])


# ─── Request / Response Schemas ──────────────────────────────────────────────


class CreateTenantRequest(BaseModel):
    name: str
    email: EmailStr
    property_id: uuid.UUID
    unit_number: str | None = None
    lease_start: date | None = None
    lease_end: date | None = None


class TenantResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    email: str
    name: str | None
    property_id: uuid.UUID
    unit_number: str | None
    lease_start: date | None
    lease_end: date | None
    invite_status: str

    model_config = {"from_attributes": True}


class CreateVendorRequest(BaseModel):
    name: str
    email: EmailStr
    phone: str | None = None
    categories: list[str] | None = None
    max_concurrent_jobs: int = 3


class VendorResponse(BaseModel):
    id: uuid.UUID
    name: str
    email: str | None
    phone: str | None
    categories: list[str] | None
    max_concurrent_jobs: int
    invite_status: str

    model_config = {"from_attributes": True}


# ─── Endpoints ───────────────────────────────────────────────────────────────


@router.post("/tenants", response_model=TenantResponse, status_code=status.HTTP_201_CREATED)
def create_tenant(
    body: CreateTenantRequest,
    pm: PMUserDep,
    db: DbDep,
) -> TenantResponse:
    """Create a tenant user, link to a property, and send an invite email."""
    try:
        # Verify the property exists and belongs to this PM
        prop: Property | None = db.get(Property, body.property_id)
        if prop is None or prop.pm_id != pm.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Property not found.",
            )

        # Check for duplicate email
        existing = db.query(User).filter(User.email == body.email).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A user with this email already exists.",
            )

        # Create User record
        user = User(
            email=body.email,
            full_name=body.name,
            role="tenant",
            invite_status="pending",
        )
        db.add(user)
        db.flush()

        # Create Tenant record
        tenant = Tenant(
            user_id=user.id,
            property_id=body.property_id,
            unit_number=body.unit_number,
            lease_start=body.lease_start,
            lease_end=body.lease_end,
        )
        db.add(tenant)
        db.flush()

        # Generate invite token and send email
        token = create_token(user_id=user.id, role="tenant", token_type="invite")
        send_invite_email(to_email=body.email, name=body.name, role="tenant", token=token)

        db.commit()
        db.refresh(tenant)
        db.refresh(user)

        return TenantResponse(
            id=tenant.id,
            user_id=user.id,
            email=user.email,
            name=user.full_name,
            property_id=tenant.property_id,
            unit_number=tenant.unit_number,
            lease_start=tenant.lease_start,
            lease_end=tenant.lease_end,
            invite_status=user.invite_status,
        )
    except HTTPException:
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create tenant: {exc}",
        )


@router.post("/vendors", response_model=VendorResponse, status_code=status.HTTP_201_CREATED)
def create_vendor(
    body: CreateVendorRequest,
    pm: PMUserDep,
    db: DbDep,
) -> VendorResponse:
    """Create a vendor user, link to the PM, and send an invite email."""
    try:
        # Check for duplicate email
        existing = db.query(User).filter(User.email == body.email).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A user with this email already exists.",
            )

        # Create User record
        user = User(
            email=body.email,
            full_name=body.name,
            phone=body.phone,
            role="vendor",
            invite_status="pending",
        )
        db.add(user)
        db.flush()

        # Create Vendor record
        vendor = Vendor(
            pm_id=pm.id,
            name=body.name,
            email=body.email,
            phone=body.phone,
            categories=body.categories,
            max_concurrent_jobs=body.max_concurrent_jobs,
        )
        db.add(vendor)
        db.flush()

        # Generate invite token and send email
        token = create_token(user_id=user.id, role="vendor", token_type="invite")
        send_invite_email(to_email=body.email, name=body.name, role="vendor", token=token)

        db.commit()
        db.refresh(vendor)
        db.refresh(user)

        return VendorResponse(
            id=vendor.id,
            name=vendor.name,
            email=vendor.email,
            phone=vendor.phone,
            categories=vendor.categories,
            max_concurrent_jobs=vendor.max_concurrent_jobs,
            invite_status=user.invite_status,
        )
    except HTTPException:
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create vendor: {exc}",
        )


@router.get("/tenants", response_model=list[TenantResponse])
def list_tenants(
    pm: PMUserDep,
    db: DbDep,
    invite_status: str | None = None,
) -> list[TenantResponse]:
    """Return all tenants across properties managed by the current PM."""
    try:
        query = (
            db.query(Tenant)
            .join(Property, Tenant.property_id == Property.id)
            .join(User, Tenant.user_id == User.id)
            .filter(Property.pm_id == pm.id)
            .options(joinedload(Tenant.user))
        )

        if invite_status is not None:
            query = query.filter(User.invite_status == invite_status)

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
            )
            for t in tenants
        ]
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list tenants: {exc}",
        )


@router.get("/vendors", response_model=list[VendorResponse])
def list_vendors(
    pm: PMUserDep,
    db: DbDep,
    invite_status: str | None = None,
) -> list[VendorResponse]:
    """Return all vendors managed by the current PM."""
    try:
        # Look up vendors joined with their user record for invite_status
        query = (
            db.query(Vendor, User)
            .join(User, Vendor.email == User.email)
            .filter(Vendor.pm_id == pm.id)
        )

        if invite_status is not None:
            query = query.filter(User.invite_status == invite_status)

        results = query.all()

        return [
            VendorResponse(
                id=v.id,
                name=v.name,
                email=v.email,
                phone=v.phone,
                categories=v.categories,
                max_concurrent_jobs=v.max_concurrent_jobs,
                invite_status=u.invite_status,
            )
            for v, u in results
        ]
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list vendors: {exc}",
        )
