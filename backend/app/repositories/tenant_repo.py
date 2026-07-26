"""app/repositories/tenant_repo.py"""
from __future__ import annotations

import uuid

from sqlalchemy.orm import joinedload

from app.models.property import Property
from app.models.tenant import Tenant
from app.repositories.base import BaseRepository


class TenantRepository(BaseRepository[Tenant]):
    model = Tenant

    def list_for_pm(
        self,
        pm_id: uuid.UUID,
        property_id: uuid.UUID | None = None,
    ) -> list[Tenant]:
        """
        Active tenants across the PM's properties.

        The join to Property is what scopes the result to this PM; the eager load
        of `user` supplies email, name, and invite_status without an N+1.
        """
        query = (
            self.db.query(Tenant)
            .join(Property, Tenant.property_id == Property.id)
            .filter(Property.pm_id == pm_id, Tenant.is_active.is_(True))
            .options(joinedload(Tenant.user))
        )

        if property_id is not None:
            query = query.filter(Tenant.property_id == property_id)

        return query.all()

    def get_for_pm(self, tenant_id: uuid.UUID, pm_id: uuid.UUID) -> Tenant | None:
        return (
            self.db.query(Tenant)
            .join(Property, Tenant.property_id == Property.id)
            .options(joinedload(Tenant.user))
            .filter(
                Tenant.id == tenant_id,
                Property.pm_id == pm_id,
                Tenant.is_active.is_(True),
            )
            .first()
        )

    def get_active_by_user_id(self, user_id: uuid.UUID) -> Tenant | None:
        """The tenant profile behind a signed-in tenant user."""
        return (
            self.db.query(Tenant)
            .filter(Tenant.user_id == user_id, Tenant.is_active.is_(True))
            .first()
        )

    def get_any_by_user_id(self, user_id: uuid.UUID) -> Tenant | None:
        """
        Ignores `is_active` — a deactivated tenant should still see an empty list
        rather than someone else's tickets.
        """
        return self.db.query(Tenant).filter(Tenant.user_id == user_id).first()
