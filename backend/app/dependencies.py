"""
app/dependencies.py

Shared FastAPI dependencies: the database session, the authenticated user, role
guards, and a provider per service.
"""
from __future__ import annotations

from typing import Annotated

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import decode_token
from app.database import get_db
from app.exceptions import ForbiddenError, NotAuthenticatedError
from app.models.user import User
from app.services.auth_service import AuthService
from app.services.category_service import CategoryService
from app.services.negotiation_service import NegotiationService
from app.services.property_service import PropertyService
from app.services.tenant_service import TenantService
from app.services.ticket_service import TicketService
from app.services.vendor_service import VendorService

# auto_error=False so a missing header becomes our own 401 NOT_AUTHENTICATED
# rather than HTTPBearer's bare 403.
_bearer = HTTPBearer(auto_error=False)

DbDep = Annotated[Session, Depends(get_db)]
BearerDep = Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)]


# ─── Authentication ──────────────────────────────────────────────────────────


def get_current_user(credentials: BearerDep, db: DbDep) -> User:
    """
    Decode the Bearer token and load its user.

    Every failure — missing header, bad signature, expired, wrong token type,
    unknown or disabled user — is reported identically, so the response never
    confirms which.
    """
    if credentials is None:
        raise NotAuthenticatedError()

    try:
        payload = decode_token(credentials.credentials)
    except (jwt.ExpiredSignatureError, jwt.PyJWTError):
        raise NotAuthenticatedError()

    # Only a login token authenticates a session. Without this check an invite
    # token — which carries the same `sub` — works as a Bearer token, and every
    # new token type widens that hole. "job" tokens are safe by accident (their
    # `sub` is a vendor_jobs.id, so the lookup below misses), but relying on an
    # accident is not a guard.
    if payload.get("type") != "login":
        raise NotAuthenticatedError()

    user_id: str | None = payload.get("sub")
    if user_id is None:
        raise NotAuthenticatedError()

    user: User | None = db.get(User, user_id)
    if user is None or not user.is_active:
        raise NotAuthenticatedError()

    return user


CurrentUserDep = Annotated[User, Depends(get_current_user)]


# ─── Role guards ─────────────────────────────────────────────────────────────


def require_pm(user: CurrentUserDep) -> User:
    if user.role != "pm":
        raise ForbiddenError("Property manager access required.")
    return user


def require_tenant(user: CurrentUserDep) -> User:
    """Only tenants file tickets — a PM or vendor cannot report on their behalf."""
    if user.role != "tenant":
        raise ForbiddenError("Only tenants can create tickets.")
    return user


PMUserDep = Annotated[User, Depends(require_pm)]
TenantUserDep = Annotated[User, Depends(require_tenant)]


# ─── Services ────────────────────────────────────────────────────────────────


def get_auth_service(db: DbDep) -> AuthService:
    return AuthService(db)


def get_property_service(db: DbDep) -> PropertyService:
    return PropertyService(db)


def get_tenant_service(db: DbDep) -> TenantService:
    return TenantService(db)


def get_vendor_service(db: DbDep) -> VendorService:
    return VendorService(db)


def get_ticket_service(db: DbDep) -> TicketService:
    return TicketService(db)


def get_category_service(db: DbDep) -> CategoryService:
    return CategoryService(db)


def get_negotiation_service(db: DbDep) -> NegotiationService:
    return NegotiationService(db)


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
PropertyServiceDep = Annotated[PropertyService, Depends(get_property_service)]
TenantServiceDep = Annotated[TenantService, Depends(get_tenant_service)]
VendorServiceDep = Annotated[VendorService, Depends(get_vendor_service)]
TicketServiceDep = Annotated[TicketService, Depends(get_ticket_service)]
CategoryServiceDep = Annotated[CategoryService, Depends(get_category_service)]
NegotiationServiceDep = Annotated[NegotiationService, Depends(get_negotiation_service)]
