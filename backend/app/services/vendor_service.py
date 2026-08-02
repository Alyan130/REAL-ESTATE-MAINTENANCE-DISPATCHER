"""
app/services/vendor_service.py

The vendor pool the dispatch agent selects from. A vendor's `categories`,
`rating`, and `max_concurrent_jobs` are the only inputs to that selection, so
this service is effectively the AI's configuration surface.
"""
from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.exceptions import (
    DuplicateEmailError,
    InviteAlreadyAcceptedError,
    NotFoundError,
    UnknownCategoryError,
    ValidationError,
)
from app.models.user import User
from app.models.vendor import Vendor
from app.repositories.user_repo import UserRepository
from app.repositories.vendor_repo import VendorRepository
from app.schemas.vendors import CreateVendorRequest, VendorInviteResponse, VendorResponse
from app.services.base import BaseService
from app.services.category_service import CategoryService
from app.services.invites import issue_invite


class VendorService(BaseService):
    def __init__(self, db: Session) -> None:
        super().__init__(db)
        self.vendors = VendorRepository(db)
        self.users = UserRepository(db)
        self.categories = CategoryService(db)

    def list_for_pm(self, pm_id: uuid.UUID) -> list[VendorResponse]:
        return [
            self._to_response(vendor, user)
            for vendor, user in self.vendors.list_active_with_user(pm_id)
        ]

    def get_for_pm(self, vendor_id: uuid.UUID, pm_id: uuid.UUID) -> VendorResponse:
        result = self.vendors.get_with_user(vendor_id, pm_id)
        if result is None:
            raise NotFoundError("Vendor not found.")
        return self._to_response(*result)

    def create_invite(
        self, pm_id: uuid.UUID, data: CreateVendorRequest
    ) -> VendorInviteResponse:
        if self.users.exists_with_email(data.email):
            raise DuplicateEmailError()

        categories = self._validated_categories(pm_id, data.categories)

        user = self.users.add(
            User(
                email=data.email,
                full_name=data.name,
                phone=data.phone,
                role="vendor",
                invite_status="pending",
            )
        )
        self.users.flush()

        vendor = self.vendors.add(
            Vendor(
                pm_id=pm_id,
                name=data.name,
                email=data.email,
                phone=data.phone,
                categories=categories,
                max_concurrent_jobs=data.max_concurrent_jobs,
            )
        )
        self.vendors.flush()

        issue_invite(user, data.name)

        self._commit()
        self.db.refresh(vendor)
        self.db.refresh(user)

        return VendorInviteResponse(
            id=vendor.id,
            name=vendor.name,
            email=vendor.email,
            phone=vendor.phone,
            categories=vendor.categories,
            max_concurrent_jobs=vendor.max_concurrent_jobs,
            invite_status=user.invite_status,
        )

    def resend_invite(self, vendor_id: uuid.UUID, pm_id: uuid.UUID) -> None:
        vendor = self._owned_or_404(vendor_id, pm_id)

        if not vendor.email:
            raise ValidationError("Vendor has no email address.")

        user = self.users.get_by_email(vendor.email)
        if user is None:
            raise NotFoundError("User not found.")

        if user.invite_status != "pending":
            raise InviteAlreadyAcceptedError()

        issue_invite(user, user.full_name or vendor.name)
        self._commit()

    def deactivate(self, vendor_id: uuid.UUID, pm_id: uuid.UUID) -> None:
        """Drops them from AI selection and disables the login behind the email."""
        vendor = self._owned_or_404(vendor_id, pm_id)
        self.vendors.deactivate(vendor)

        if vendor.email:
            user = self.users.get_by_email(vendor.email)
            if user:
                user.is_active = False

        self._commit()

    # ─── Internals ───────────────────────────────────────────────────────────

    def _validated_categories(
        self, pm_id: uuid.UUID, requested: list[str] | None
    ) -> list[str] | None:
        """
        Check the requested categories against this PM's own vocabulary.

        A vendor tagged with a category the PM doesn't have can never be
        matched by `find_best_vendor`, so accepting one would silently create a
        vendor that never receives work. `other` is rejected too: it is the
        intake fallback, and a vendor covering it would defeat the escalation
        that unclassifiable tickets depend on.
        """
        if not requested:
            return requested

        allowed = set(
            self.categories.allowed_names(pm_id, vendor_selectable_only=True)
        )
        unknown = [name for name in requested if name not in allowed]
        if unknown:
            raise UnknownCategoryError(
                f"Not a category you have: {', '.join(sorted(set(unknown)))}."
            )

        # De-duplicate while preserving the order the PM chose.
        return list(dict.fromkeys(requested))

    def _owned_or_404(self, vendor_id: uuid.UUID, pm_id: uuid.UUID) -> Vendor:
        vendor = self.vendors.get_owned(vendor_id, pm_id)
        if vendor is None:
            raise NotFoundError("Vendor not found.")
        return vendor

    @staticmethod
    def _to_response(vendor: Vendor, user: User) -> VendorResponse:
        return VendorResponse(
            id=vendor.id,
            name=vendor.name,
            email=vendor.email,
            phone=vendor.phone,
            categories=vendor.categories,
            max_concurrent_jobs=vendor.max_concurrent_jobs,
            rating=float(vendor.rating),
            invite_status=user.invite_status,
            is_active=vendor.is_active,
        )
