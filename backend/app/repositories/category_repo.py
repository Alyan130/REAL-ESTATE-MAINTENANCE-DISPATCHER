"""app/repositories/category_repo.py"""
from __future__ import annotations

import uuid

from app.models.category_setting import CategorySetting
from app.repositories.base import BaseRepository


class CategoryRepository(BaseRepository[CategorySetting]):
    model = CategorySetting

    def list_for_pm(
        self, pm_id: uuid.UUID, *, vendor_selectable_only: bool = False
    ) -> list[CategorySetting]:
        """Active categories in the PM's chosen display order."""
        query = self.db.query(CategorySetting).filter(
            CategorySetting.pm_id == pm_id,
            CategorySetting.is_active.is_(True),
        )
        if vendor_selectable_only:
            query = query.filter(CategorySetting.is_vendor_selectable.is_(True))
        return query.order_by(
            CategorySetting.sort_order.asc(), CategorySetting.label.asc()
        ).all()

    def get_owned(
        self, category_id: uuid.UUID, pm_id: uuid.UUID
    ) -> CategorySetting | None:
        return (
            self.db.query(CategorySetting)
            .filter(
                CategorySetting.id == category_id,
                CategorySetting.pm_id == pm_id,
                CategorySetting.is_active.is_(True),
            )
            .first()
        )

    def get_by_name(self, pm_id: uuid.UUID, name: str) -> CategorySetting | None:
        """Includes soft-deleted rows — the unique constraint spans them too, so a
        re-created category must reactivate the existing row, not insert a second."""
        return (
            self.db.query(CategorySetting)
            .filter(CategorySetting.pm_id == pm_id, CategorySetting.name == name)
            .first()
        )

    def has_any(self, pm_id: uuid.UUID) -> bool:
        return (
            self.db.query(CategorySetting.id)
            .filter(CategorySetting.pm_id == pm_id)
            .first()
            is not None
        )

    def next_sort_order(self, pm_id: uuid.UUID) -> int:
        rows = (
            self.db.query(CategorySetting.sort_order)
            .filter(CategorySetting.pm_id == pm_id)
            .all()
        )
        return max((row[0] for row in rows), default=-1) + 1

    def deactivate(self, category: CategorySetting) -> None:
        """Soft delete. `tickets.category` is free text with no FK, so a hard
        delete would orphan every historical ticket in this category."""
        category.is_active = False
