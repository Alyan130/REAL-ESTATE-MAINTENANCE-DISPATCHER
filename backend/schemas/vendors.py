"""
schemas/vendors.py

Pydantic models for vendor management and invite endpoints.

- CreateVendorRequest  : body for POST /auth/invites/vendors
- VendorInviteResponse : slimmer response returned right after invite creation
- VendorResponse       : full vendor detail response (includes is_active, rating)
                         used by GET /vendors and GET /vendors/{id}
"""
from __future__ import annotations

import uuid

from pydantic import BaseModel, EmailStr


class CreateVendorRequest(BaseModel):
    name: str
    email: EmailStr
    phone: str | None = None
    categories: list[str] | None = None
    max_concurrent_jobs: int = 3


class VendorInviteResponse(BaseModel):
    """Returned immediately after a vendor invite is created.  No is_active/rating fields."""

    id: uuid.UUID
    name: str
    email: str | None
    phone: str | None
    categories: list[str] | None
    max_concurrent_jobs: int
    invite_status: str

    model_config = {"from_attributes": True}


class VendorResponse(BaseModel):
    """Full vendor detail including activation status and rating."""

    id: uuid.UUID
    name: str
    email: str | None
    phone: str | None
    categories: list[str] | None
    max_concurrent_jobs: int
    rating: float
    invite_status: str
    is_active: bool

    model_config = {"from_attributes": True}
