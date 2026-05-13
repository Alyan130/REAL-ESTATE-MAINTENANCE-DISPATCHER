"""
schemas/__init__.py

Re-exports all Pydantic schemas for convenient top-level imports.
"""
from schemas.auth import AcceptInviteRequest, LoginRequest, ResendInviteResponse, TokenResponse
from schemas.properties import CreatePropertyRequest, PropertyResponse
from schemas.tenants import CreateTenantRequest, TenantInviteResponse, TenantResponse
from schemas.tickets import (
    StatusUpdateResponse,
    TicketCreatedResponse,
    TicketResponse,
    UpdateStatusRequest,
)
from schemas.vendors import CreateVendorRequest, VendorInviteResponse, VendorResponse

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
