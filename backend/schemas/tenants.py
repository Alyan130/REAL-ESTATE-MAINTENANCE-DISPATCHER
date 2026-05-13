"""
schemas/tenants.py

Pydantic models for tenant management and invite endpoints.

- CreateTenantRequest  : body for POST /auth/invites/tenants
- TenantInviteResponse : slimmer response returned right after invite creation
- TenantResponse       : full tenant detail response (includes is_active) used by
                         GET /tenants and GET /tenants/{id}
"""
from __future__ import annotations

import uuid
from datetime import date

from pydantic import BaseModel, EmailStr


class CreateTenantRequest(BaseModel):
    name: str
    email: EmailStr
    property_id: uuid.UUID
    unit_number: str | None = None
    lease_start: date | None = None
    lease_end: date | None = None


class TenantInviteResponse(BaseModel):
    """Returned immediately after a tenant invite is created.  No is_active field."""

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


class TenantResponse(BaseModel):
    """Full tenant detail including account activation status."""

    id: uuid.UUID
    user_id: uuid.UUID
    email: str
    name: str | None
    property_id: uuid.UUID
    unit_number: str | None
    lease_start: date | None
    lease_end: date | None
    invite_status: str
    is_active: bool

    model_config = {"from_attributes": True}
