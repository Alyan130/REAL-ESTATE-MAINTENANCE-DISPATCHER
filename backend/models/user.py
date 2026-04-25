import uuid
from sqlalchemy import Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy import DateTime
from .base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    full_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    phone: Mapped[str | None] = mapped_column(Text, nullable=True)
    role: Mapped[str] = mapped_column(String(20), nullable=False)  # 'pm' | 'tenant' | 'vendor'
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # Relationships
    properties = relationship("Property", back_populates="pm", foreign_keys="Property.pm_id")
    vendors = relationship("Vendor", back_populates="pm", foreign_keys="Vendor.pm_id")
    tenant_profile = relationship("Tenant", back_populates="user", foreign_keys="Tenant.user_id")
    notifications = relationship("Notification", back_populates="user", foreign_keys="Notification.user_id")
