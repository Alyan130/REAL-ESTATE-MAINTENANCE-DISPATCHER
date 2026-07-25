"""
app/api/v1/auth.py

Authentication and invitation routes.

Tenant and vendor creation live here rather than on their own routers because
an invite *is* how those accounts come into existence — the handlers delegate to
the matching domain service.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, status

from app.dependencies import AuthServiceDep, PMUserDep, TenantServiceDep, VendorServiceDep
from app.schemas.auth import (
    AcceptInviteRequest,
    LoginRequest,
    ResendInviteResponse,
    TokenResponse,
)
from app.schemas.tenants import CreateTenantRequest, TenantInviteResponse
from app.schemas.vendors import CreateVendorRequest, VendorInviteResponse

router = APIRouter(prefix="/auth", tags=["auth"])


# ─── Auth ────────────────────────────────────────────────────────────────────


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, service: AuthServiceDep) -> TokenResponse:
    """
    Authenticate a user and return a signed JWT.

    - 401 if the email is unknown or the password is wrong (indistinguishable).
    - 403 if the invite has not been accepted yet.
    - 401 if the account is disabled.
    """
    return service.login(body)


@router.post("/accept-invite", response_model=TokenResponse)
def accept_invite(body: AcceptInviteRequest, service: AuthServiceDep) -> TokenResponse:
    """
    Accept an invite by setting an initial password, and return a login JWT.

    - 400 for mismatched passwords, a malformed token, or an already-used invite.
    - 410 if the token has expired or been superseded by a newer invite.
    """
    return service.accept_invite(body)


# ─── Invites ─────────────────────────────────────────────────────────────────


@router.post(
    "/invites/tenants",
    response_model=TenantInviteResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["invites"],
)
def create_tenant(
    body: CreateTenantRequest,
    pm: PMUserDep,
    service: TenantServiceDep,
) -> TenantInviteResponse:
    """Create a tenant user, link them to a property, and send the invite email."""
    return service.create_invite(pm.id, body)


@router.post(
    "/invites/vendors",
    response_model=VendorInviteResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["invites"],
)
def create_vendor(
    body: CreateVendorRequest,
    pm: PMUserDep,
    service: VendorServiceDep,
) -> VendorInviteResponse:
    """Create a vendor, link them to the PM, and send the invite email."""
    return service.create_invite(pm.id, body)


@router.post(
    "/invites/tenants/{tenant_id}/resend",
    response_model=ResendInviteResponse,
    tags=["invites"],
)
def resend_tenant_invite(
    tenant_id: uuid.UUID,
    pm: PMUserDep,
    service: TenantServiceDep,
) -> ResendInviteResponse:
    """Resend a pending tenant's invite, invalidating every earlier link."""
    service.resend_invite(tenant_id, pm.id)
    return ResendInviteResponse(ok=True)


@router.post(
    "/invites/vendors/{vendor_id}/resend",
    response_model=ResendInviteResponse,
    tags=["invites"],
)
def resend_vendor_invite(
    vendor_id: uuid.UUID,
    pm: PMUserDep,
    service: VendorServiceDep,
) -> ResendInviteResponse:
    """Resend a pending vendor's invite, invalidating every earlier link."""
    service.resend_invite(vendor_id, pm.id)
    return ResendInviteResponse(ok=True)
