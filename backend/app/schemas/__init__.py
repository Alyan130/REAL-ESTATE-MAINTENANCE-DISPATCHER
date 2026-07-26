"""
schemas/__init__.py

Re-exports all Pydantic schemas for convenient top-level imports.
"""
from app.schemas.auth import AcceptInviteRequest, LoginRequest, ResendInviteResponse, TokenResponse
from app.schemas.properties import CreatePropertyRequest, PropertyResponse
from app.schemas.tenants import CreateTenantRequest, TenantInviteResponse, TenantResponse
from app.schemas.tickets import (
    StatusUpdateResponse,
    TicketCreatedResponse,
    TicketResponse,
    UpdateStatusRequest,
)
from app.schemas.vendors import CreateVendorRequest, VendorInviteResponse, VendorResponse

__all__ = [
    # auth
    "LoginRequest",
    "TokenResponse",
    "AcceptInviteRequest",
    "ResendInviteResponse",
    # properties
    "CreatePropertyRequest",
    "PropertyResponse",
    # tenants
    "CreateTenantRequest",
    "TenantResponse",
    "TenantInviteResponse",
    # vendors
    "CreateVendorRequest",
    "VendorResponse",
    "VendorInviteResponse",
    # tickets
    "TicketCreatedResponse",
    "TicketResponse",
    "UpdateStatusRequest",
    "StatusUpdateResponse",
]
