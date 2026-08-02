import uuid
from datetime import datetime

from sqlalchemy import Text, ForeignKey, Numeric, DateTime, Date, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from .base import Base

# Statuses a job can never come back from. A chat token stays valid exactly
# while the job is *not* in one of these — the status is the revocation
# mechanism, which is why no token needs to be stored anywhere.
TERMINAL_JOB_STATUSES = ["DECLINED", "EXPIRED", "SUPERSEDED", "COMPLETED"]


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
    # PENDING (offered, negotiating) → QUOTED (PM deciding) → APPROVED
    #   → COMPLETED, or DECLINED | EXPIRED | SUPERSEDED
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDING")
    quote_amount: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    quoted_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    scheduled_date: Mapped[Date | None] = mapped_column(Date, nullable=True)
    completion_photo: Mapped[str | None] = mapped_column(Text, nullable=True)
    invoice_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    invoice_amount: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    stripe_session_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    paid_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # ─── Negotiation ─────────────────────────────────────────────────────────
    # Which LangGraph thread owns this negotiation. Persisted rather than
    # derived, so a resume is always a lookup and never a guess — the fallback
    # path rebuilds on a fresh thread and writes the new id back here.
    negotiation_thread_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Idempotency guard: set once, the first time the offer actually goes out.
    # `open_negotiation` returns early when this is set, so a rebuild after a
    # checkpoint expiry cannot send a second offer email.
    negotiation_opened_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # Arbiter for the follow-up-timer-versus-vendor-reply race. Written in the
    # same transaction as the message insert.
    last_vendor_message_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # Counters live here rather than in graph state so they survive a restart
    # and a checkpoint eviction.
    followups_sent: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0", default=0
    )
    counter_rounds: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0", default=0
    )
    availability_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    declined_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    ticket = relationship("Ticket", back_populates="vendor_jobs", foreign_keys=[ticket_id])
    vendor = relationship("Vendor", back_populates="jobs", foreign_keys=[vendor_id])
    messages = relationship(
        "VendorMessage",
        back_populates="job",
        foreign_keys="VendorMessage.vendor_job_id",
        cascade="all, delete-orphan",
        order_by="VendorMessage.created_at",
    )
