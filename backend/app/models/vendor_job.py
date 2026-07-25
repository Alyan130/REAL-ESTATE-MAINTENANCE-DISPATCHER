import uuid
from sqlalchemy import Text, ForeignKey, Numeric, DateTime, Date, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from .base import Base


class VendorJob(Base):
    __tablename__ = "vendor_jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    ticket_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False
    )
    vendor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("vendors.id", ondelete="CASCADE"), nullable=False
    )
    # Status: PENDING | QUOTED | APPROVED | COMPLETED
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDING")
    quote_amount: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    quoted_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    scheduled_date: Mapped[Date | None] = mapped_column(Date, nullable=True)
    completion_photo: Mapped[str | None] = mapped_column(Text, nullable=True)
    invoice_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    invoice_amount: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    stripe_session_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    paid_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # Relationships
    ticket = relationship("Ticket", back_populates="vendor_jobs", foreign_keys=[ticket_id])
    vendor = relationship("Vendor", back_populates="jobs", foreign_keys=[vendor_id])
