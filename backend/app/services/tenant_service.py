"""
app/services/tenant_service.py

The PM's tenant roster, plus the invite flow that brings a tenant account into
existence.
"""
from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.exceptions import DuplicateEmailError, InviteAlreadyAcceptedError, NotFoundError
from app.models.tenant import Tenant
from app.models.user import User
from app.repositories.property_repo import PropertyRepository
from app.repositories.tenant_repo import TenantRepository
from app.repositories.user_repo import UserRepository
from app.schemas.tenants import CreateTenantRequest, TenantInviteResponse, TenantResponse
from app.services.base import BaseService
from app.services.invites import issue_invite


class TenantService(BaseService):
    def __init__(self, db: Session) -> None:
        super().__init__(db)
        self.tenants = TenantRepository(db)
        self.users = UserRepository(db)
        self.properties = PropertyRepository(db)

    def list_for_pm(
        self, pm_id: uuid.UUID, property_id: uuid.UUID | None = None
    ) -> list[TenantResponse]:
        return [
            self._to_response(tenant)
            for tenant in self.tenants.list_for_pm(pm_id, property_id)
        ]

    def get_for_pm(self, tenant_id: uuid.UUID, pm_id: uuid.UUID) -> TenantResponse:
        return self._to_response(self._owned_or_404(tenant_id, pm_id))

    def create_invite(
        self, pm_id: uuid.UUID, data: CreateTenantRequest
    ) -> TenantInviteResponse:
        """
        Create the user and tenant profile together and email the invite.

        Both rows and the invite stamp land in one transaction — a half-created
        tenant would be an account nobody can sign into or delete.
        """
        if self.properties.get_owned(data.property_id, pm_id) is None:
            raise NotFoundError("Property not found.")

        if self.users.exists_with_email(data.email):
            raise DuplicateEmailError()

        user = self.users.add(
            User(
                email=data.email,
                full_name=data.name,
                role="tenant",
                invite_status="pending",
            )
        )
        self.users.flush()

        tenant = self.tenants.add(
            Tenant(
                user_id=user.id,
                property_id=data.property_id,
                unit_number=data.unit_number,
                lease_start=data.lease_start,
                lease_end=data.lease_end,
            )
        )
        self.tenants.flush()

        issue_invite(user, data.name)

        self._commit()
        self.db.refresh(tenant)
        self.db.refresh(user)

        return TenantInviteResponse(
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

    def resend_invite(self, tenant_id: uuid.UUID, pm_id: uuid.UUID) -> None:
        """Sends a fresh link and invalidates every earlier one."""
        tenant = self._owned_or_404(tenant_id, pm_id)

        user = tenant.user
        if user is None:
            raise NotFoundError("User not found.")

        if user.invite_status != "pending":
            raise InviteAlreadyAcceptedError()

        issue_invite(user, user.full_name or "there")
        self._commit()

    def deactivate(self, tenant_id: uuid.UUID, pm_id: uuid.UUID) -> None:
        """Switches off the tenant profile and their login together. No undo."""
        tenant = self._owned_or_404(tenant_id, pm_id)

        tenant.is_active = False
        if tenant.user:
            tenant.user.is_active = False

        self._commit()

    # ─── Internals ───────────────────────────────────────────────────────────

    def _owned_or_404(self, tenant_id: uuid.UUID, pm_id: uuid.UUID) -> Tenant:
        tenant = self.tenants.get_for_pm(tenant_id, pm_id)
        if tenant is None:
            raise NotFoundError("Tenant not found.")
        return tenant

    @staticmethod
    def _to_response(tenant: Tenant) -> TenantResponse:
        """`invite_status` lives on the user row, so the two are stitched here."""
        return TenantResponse(
            id=tenant.id,
            user_id=tenant.user_id,
            email=tenant.user.email,
            name=tenant.user.full_name,
            property_id=tenant.property_id,
            unit_number=tenant.unit_number,
            lease_start=tenant.lease_start,
            lease_end=tenant.lease_end,
            invite_status=tenant.user.invite_status,
            is_active=tenant.is_active,
        )
