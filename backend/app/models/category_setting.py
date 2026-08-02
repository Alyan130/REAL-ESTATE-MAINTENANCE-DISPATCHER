import uuid
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from .base import Base


class CategorySetting(Base):
    """
    A PM's maintenance category, and what they are willing to pay for it.

    `name` is the slug that lands in `tickets.category` and `vendors.categories`
    — those columns are free text with no FK, which is why deletion here is a
    soft delete: removing a category must never orphan ticket history.

    The two prices drive the negotiation agent:
      - `target_price` is the anchor it negotiates toward (a historical median
        overrides it once there is enough data).
      - `max_price` is the auto-approve ceiling. NULL means "never auto-approve,
        always ask me" — the safe default for a PM who hasn't set prices yet.
    """

    __tablename__ = "category_settings"
    __table_args__ = (
        # Leads with pm_id, so a separate index on pm_id would be redundant.
        UniqueConstraint("pm_id", "name", name="uq_category_settings_pm_name"),
        CheckConstraint(
            "max_price IS NULL OR target_price IS NULL OR max_price >= target_price",
            name="ck_category_settings_price_order",
        ),
        CheckConstraint(
            "target_price IS NULL OR target_price >= 0",
            name="ck_category_settings_target_non_negative",
        ),
        CheckConstraint(
            "max_price IS NULL OR max_price >= 0",
            name="ck_category_settings_max_non_negative",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    pm_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    label: Mapped[str] = mapped_column(Text, nullable=False)
    target_price: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    max_price: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    # "other" is the intake fallback, never a vendor specialty.
    is_vendor_selectable: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    pm = relationship("User", back_populates="category_settings", foreign_keys=[pm_id])
