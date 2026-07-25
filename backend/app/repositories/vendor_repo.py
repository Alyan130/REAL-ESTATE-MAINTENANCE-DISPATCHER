"""app/repositories/vendor_repo.py"""
from __future__ import annotations

import uuid

from app.models.user import User
from app.models.vendor import Vendor
from app.repositories.base import BaseRepository


class VendorRepository(BaseRepository[Vendor]):
    model = Vendor

    def list_active_with_user(self, pm_id: uuid.UUID) -> list[tuple[Vendor, User]]:
        """
        Active vendors paired with their user row.

        `invite_status` lives on User, and Vendor has no FK to it — email is the
        only link between the two, which is why this is a join on email rather
        than a relationship.
        """
        return (
            self.db.query(Vendor, User)
            .join(User, Vendor.email == User.email)
            .filter(Vendor.pm_id == pm_id, Vendor.is_active.is_(True))
            .all()
        )

    def get_with_user(
        self, vendor_id: uuid.UUID, pm_id: uuid.UUID
    ) -> tuple[Vendor, User] | None:
        return (
            self.db.query(Vendor, User)
            .join(User, Vendor.email == User.email)
            .filter(
                Vendor.id == vendor_id,
                Vendor.pm_id == pm_id,
                Vendor.is_active.is_(True),
            )
            .first()
        )

    def get_owned(self, vendor_id: uuid.UUID, pm_id: uuid.UUID) -> Vendor | None:
        return (
            self.db.query(Vendor)
            .filter(
                Vendor.id == vendor_id,
                Vendor.pm_id == pm_id,
                Vendor.is_active.is_(True),
            )
            .first()
        )

    def deactivate(self, vendor: Vendor) -> None:
        """Removes them from AI selection. The login is disabled by the service."""
        vendor.is_active = False
