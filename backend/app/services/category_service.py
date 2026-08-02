"""
app/services/category_service.py

The PM's maintenance vocabulary and what they will pay for each trade.

Two consumers depend on this, which is why it is more than CRUD:
  - the intake agent classifies tickets into these categories,
  - the negotiation agent reads `target_price` as its anchor and `max_price` as
    the ceiling below which a vendor's quote is approved without asking the PM.

Seeding is lazy rather than tied to signup: there is no PM signup flow in this
codebase — PM rows are inserted by hand — so `ensure_seeded` is called from the
read paths instead. It is idempotent and cheap (one indexed existence check).
"""
from __future__ import annotations

import logging
import re
import uuid
from decimal import Decimal

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.categories import OTHER, SEED_CATEGORIES
from app.exceptions import (
    DuplicateCategoryError,
    NotFoundError,
    ProtectedCategoryError,
    ValidationError,
)
from app.models.category_setting import CategorySetting
from app.repositories.category_repo import CategoryRepository
from app.schemas.categories import (
    CategoryResponse,
    CreateCategoryRequest,
    UpdateCategoryRequest,
)
from app.services.base import BaseService

logger = logging.getLogger(__name__)

_SLUG_STRIP = re.compile(r"[^a-z0-9]+")


def slugify(value: str) -> str:
    """'Air Conditioning' → 'air-conditioning'. The slug is what lands in
    `tickets.category`, so it must be stable and lowercase."""
    return _SLUG_STRIP.sub("-", value.strip().lower()).strip("-")


class CategoryService(BaseService):
    def __init__(self, db: Session) -> None:
        super().__init__(db)
        self.categories = CategoryRepository(db)

    # ─── Reads ───────────────────────────────────────────────────────────────

    def list_for_pm(
        self, pm_id: uuid.UUID, *, vendor_selectable_only: bool = False
    ) -> list[CategoryResponse]:
        self.ensure_seeded(pm_id)
        return [
            self._to_response(category)
            for category in self.categories.list_for_pm(
                pm_id, vendor_selectable_only=vendor_selectable_only
            )
        ]

    def allowed_names(
        self, pm_id: uuid.UUID, *, vendor_selectable_only: bool = False
    ) -> list[str]:
        """The slugs this PM may use. Callers validate against this rather than a
        hardcoded list — that is the whole point of the table."""
        self.ensure_seeded(pm_id)
        return [
            category.name
            for category in self.categories.list_for_pm(
                pm_id, vendor_selectable_only=vendor_selectable_only
            )
        ]

    # ─── Writes ──────────────────────────────────────────────────────────────

    def ensure_seeded(self, pm_id: uuid.UUID) -> None:
        """Give a PM the starter vocabulary if they have none.

        Prices are left NULL: a NULL `max_price` means "never auto-approve", so
        a freshly seeded PM is never spending money they haven't authorised.
        """
        if self.categories.has_any(pm_id):
            return

        for order, (name, label, selectable) in enumerate(SEED_CATEGORIES):
            self.categories.add(
                CategorySetting(
                    pm_id=pm_id,
                    name=name,
                    label=label,
                    is_vendor_selectable=selectable,
                    sort_order=order,
                )
            )

        try:
            self._commit()
        except IntegrityError:
            # Two first-loads raced (two tabs, say) and the other one seeded
            # first. The unique constraint did its job; the rows we wanted now
            # exist, so this is success, not an error worth showing anyone.
            self.db.rollback()
            logger.info("Category seed for PM %s lost a race; rows already exist", pm_id)

    def create(self, pm_id: uuid.UUID, data: CreateCategoryRequest) -> CategoryResponse:
        self.ensure_seeded(pm_id)

        name = slugify(data.name or data.label)
        if not name:
            raise ValidationError("Category name must contain letters or numbers.")

        existing = self.categories.get_by_name(pm_id, name)
        if existing is not None:
            # A soft-deleted row still occupies the unique constraint, so
            # re-adding a removed category revives it rather than colliding.
            if existing.is_active:
                raise DuplicateCategoryError()
            existing.is_active = True
            existing.label = data.label
            existing.target_price = data.target_price
            existing.max_price = data.max_price
            self._commit()
            self.db.refresh(existing)
            return self._to_response(existing)

        category = self.categories.add(
            CategorySetting(
                pm_id=pm_id,
                name=name,
                label=data.label,
                target_price=data.target_price,
                max_price=data.max_price,
                is_vendor_selectable=True,
                sort_order=self.categories.next_sort_order(pm_id),
            )
        )
        self._commit()
        self.db.refresh(category)
        return self._to_response(category)

    def update(
        self, category_id: uuid.UUID, pm_id: uuid.UUID, data: UpdateCategoryRequest
    ) -> CategoryResponse:
        category = self._owned_or_404(category_id, pm_id)

        # exclude_unset so "field omitted" stays distinct from "field set to
        # null" — clearing max_price is how a PM turns auto-approval back off.
        changes = data.model_dump(exclude_unset=True)
        for field, value in changes.items():
            setattr(category, field, value)

        # Re-check against the merged row, not just the payload: raising one
        # price alone can still invert the pair.
        target: Decimal | None = category.target_price
        ceiling: Decimal | None = category.max_price
        if target is not None and ceiling is not None and ceiling < target:
            raise ValidationError(
                "The auto-approve ceiling can't be below the target price."
            )

        # The slug is never renamed — historical tickets reference it by value.
        self._commit()
        self.db.refresh(category)
        return self._to_response(category)

    def deactivate(self, category_id: uuid.UUID, pm_id: uuid.UUID) -> None:
        category = self._owned_or_404(category_id, pm_id)
        if category.name == OTHER:
            raise ProtectedCategoryError()

        self.categories.deactivate(category)
        self._commit()

    # ─── Internals ───────────────────────────────────────────────────────────

    def _owned_or_404(
        self, category_id: uuid.UUID, pm_id: uuid.UUID
    ) -> CategorySetting:
        category = self.categories.get_owned(category_id, pm_id)
        if category is None:
            raise NotFoundError("Category not found.")
        return category

    @staticmethod
    def _to_response(category: CategorySetting) -> CategoryResponse:
        return CategoryResponse(
            id=category.id,
            name=category.name,
            label=category.label,
            target_price=(
                float(category.target_price)
                if category.target_price is not None
                else None
            ),
            max_price=(
                float(category.max_price) if category.max_price is not None else None
            ),
            is_vendor_selectable=category.is_vendor_selectable,
            sort_order=category.sort_order,
        )
