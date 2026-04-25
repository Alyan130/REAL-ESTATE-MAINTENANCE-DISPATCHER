import uuid
from sqlalchemy import Boolean, Text, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy import String
from sqlalchemy.sql import func
from .base import Base


class Ticket(Base):
    __tablename__ = "tickets"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    property_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("properties.id", ondelete="CASCADE"), nullable=False
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str | None] = mapped_column(Text, nullable=True)
    priority: Mapped[str | None] = mapped_column(String(10), nullable=True)  # P1–P4
    # Status state machine:
    # OPEN → TRIAGED → PENDING_APPROVAL → DISPATCHED → QUOTED → APPROVED →
    # SCHEDULED → IN_PROGRESS → COMPLETED → INVOICED → CLOSED | CANCELLED
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="OPEN")
    media_urls: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)
    ai_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    permission_to_enter: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    property = relationship("Property", back_populates="tickets", foreign_keys=[property_id])
    tenant = relationship("Tenant", back_populates="tickets", foreign_keys=[tenant_id])
    vendor_jobs = relationship("VendorJob", back_populates="ticket", foreign_keys="VendorJob.ticket_id")
