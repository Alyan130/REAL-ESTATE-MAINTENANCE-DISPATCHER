"""
api/routes/auth.py

Authentication and invitation routes.
"""
from __future__ import annotations

import uuid
from datetime import date
from typing import Annotated

import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session, joinedload

from api.deps import DbDep, PMUserDep
from core.email import send_invite_email
from core.security import create_token, decode_token, hash_password, verify_password
from database import get_db
from models.property import Property
from models.tenant import Tenant
from models.user import User
from models.vendor import Vendor

router = APIRouter(prefix="/auth", tags=["auth"])

# ─── Schemas ──────────────────────────────────────────────────────────────────


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class AcceptInviteRequest(BaseModel):
    token: str
    password: str
    confirm_password: str


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


class ResendInviteResponse(BaseModel):
    ok: bool = True


# ─── Auth Endpoints ──────────────────────────────────────────────────────────


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: DbDep) -> TokenResponse:
    """
    Authenticate a user and return a signed JWT.

    - 401 if email not found or password is wrong.
    - 403 if the user's invite_status is still 'pending'.
    - 200 + JWT on success.
    """
    user: User | None = (
        db.query(User).filter(User.email == body.email).first()
    )

    # Email not found OR password mismatch → same generic 401
    if user is None or not verify_password(body.password, user.password_hash or ""):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    # Account not yet approved
    if user.invite_status != "approved":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account is pending approval.",
        )

    # Inactive account
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is disabled.",
        )

    token = create_token(
        user_id=user.id,
        role=user.role,
        token_type="login",
    )
    return TokenResponse(access_token=token)


@router.post("/accept-invite", response_model=TokenResponse)
def accept_invite(body: AcceptInviteRequest, db: DbDep) -> TokenResponse:
    """
    Accept an invite token by setting an initial password.

    Returns a login JWT on success.

    - 400 for invalid input or invalid token type.
    - 404 if the user no longer exists.
    - 410 if the invite token is expired or superseded.
    """
    try:
        if body.password != body.confirm_password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Passwords do not match.",
            )

        try:
            payload = decode_token(body.token)
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_410_GONE,
                detail="Invite token has expired.",
            )
        except jwt.PyJWTError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid invite token.",
            )

        if payload.get("type") != "invite":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid token type.",
            )

        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid token payload.",
            )

        user: User | None = db.get(User, user_id)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found.",
            )

        if user.invite_status != "pending":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invite already accepted.",
            )

        token_role = payload.get("role")
        if token_role and token_role != user.role:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid invite token.",
            )

        token_iat_raw = payload.get("iat")
        token_iat: int | None = None
        if token_iat_raw is not None:
            try:
                token_iat = int(token_iat_raw)
            except (TypeError, ValueError):
                token_iat = None

        if (
            user.last_invite_iat is not None
            and token_iat is not None
            and token_iat < user.last_invite_iat
        ):
            raise HTTPException(
                status_code=status.HTTP_410_GONE,
                detail="Invite token has been superseded.",
            )

        user.password_hash = hash_password(body.password)
        user.invite_status = "approved"
        user.last_invite_iat = None
        db.commit()
        db.refresh(user)

        login_token = create_token(
            user_id=user.id,
            role=user.role,
            token_type="login",
        )
        return TokenResponse(access_token=login_token)
    except HTTPException:
        raise
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to accept invite.",
        )


# ─── Invite Endpoints ───────────────────────────────────────────────────────


@router.post(
    "/invites/tenants",
    response_model=TenantResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["invites"],
)
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
        payload = decode_token(token)
        iat_raw = payload.get("iat")
        try:
            user.last_invite_iat = int(iat_raw) if iat_raw is not None else None
        except (TypeError, ValueError):
            user.last_invite_iat = None
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


@router.post(
    "/invites/vendors",
    response_model=VendorResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["invites"],
)
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
        payload = decode_token(token)
        iat_raw = payload.get("iat")
        try:
            user.last_invite_iat = int(iat_raw) if iat_raw is not None else None
        except (TypeError, ValueError):
            user.last_invite_iat = None
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


@router.post(
    "/invites/tenants/{tenant_id}/resend",
    response_model=ResendInviteResponse,
    tags=["invites"],
)
def resend_tenant_invite(
    tenant_id: uuid.UUID,
    pm: PMUserDep,
    db: DbDep,
) -> ResendInviteResponse:
    """Resend an invite email to a pending tenant (invalidates older invite tokens)."""
    try:
        tenant: Tenant | None = (
            db.query(Tenant)
            .join(Property, Tenant.property_id == Property.id)
            .options(joinedload(Tenant.user))
            .filter(Tenant.id == tenant_id, Property.pm_id == pm.id)
            .first()
        )
        if tenant is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tenant not found.",
            )

        user: User | None = tenant.user
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found.",
            )

        if user.invite_status != "pending":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invite already accepted.",
            )

        token = create_token(user_id=user.id, role=user.role, token_type="invite")
        payload = decode_token(token)
        iat_raw = payload.get("iat")
        try:
            user.last_invite_iat = int(iat_raw) if iat_raw is not None else None
        except (TypeError, ValueError):
            user.last_invite_iat = None

        send_invite_email(
            to_email=user.email,
            name=user.full_name or "there",
            role=user.role,
            token=token,
        )
        db.commit()
        return ResendInviteResponse(ok=True)
    except HTTPException:
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to resend invite: {exc}",
        )


@router.post(
    "/invites/vendors/{vendor_id}/resend",
    response_model=ResendInviteResponse,
    tags=["invites"],
)
def resend_vendor_invite(
    vendor_id: uuid.UUID,
    pm: PMUserDep,
    db: DbDep,
) -> ResendInviteResponse:
    """Resend an invite email to a pending vendor (invalidates older invite tokens)."""
    try:
        vendor: Vendor | None = (
            db.query(Vendor)
            .filter(Vendor.id == vendor_id, Vendor.pm_id == pm.id)
            .first()
        )
        if vendor is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Vendor not found.",
            )

        if not vendor.email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Vendor has no email address.",
            )

        user: User | None = db.query(User).filter(User.email == vendor.email).first()
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found.",
            )

        if user.invite_status != "pending":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invite already accepted.",
            )

        token = create_token(user_id=user.id, role=user.role, token_type="invite")
        payload = decode_token(token)
        iat_raw = payload.get("iat")
        try:
            user.last_invite_iat = int(iat_raw) if iat_raw is not None else None
        except (TypeError, ValueError):
            user.last_invite_iat = None

        send_invite_email(
            to_email=user.email,
            name=user.full_name or vendor.name,
            role=user.role,
            token=token,
        )
        db.commit()
        return ResendInviteResponse(ok=True)
    except HTTPException:
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to resend invite: {exc}",
        )
