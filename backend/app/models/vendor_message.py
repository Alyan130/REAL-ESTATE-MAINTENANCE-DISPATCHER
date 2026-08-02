import uuid

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from .base import Base


class VendorMessage(Base):
    """
    One turn of the negotiation transcript, scoped to a single VendorJob.

    The transcript lives in Postgres rather than in LangGraph state for four
    reasons, all of which bite in practice:

      - The Redis checkpoint has a 3-day TTL, which is shorter than a P4
        negotiation window. A vendor replying on day four would otherwise be
        talking to an agent with no memory of the conversation.
      - The vendor chat page must render history with no live graph running.
      - The PM reads the same transcript over plain REST.
      - Graph state is per-*ticket*, while messages are per-*VendorJob* — vendor
        #2 runs on the very same TicketState as vendor #1.

    `extracted` holds the structured output the model produced for a vendor
    message: price, availability, intent, and whether it recommended approval.
    Keeping it alongside the raw text is what lets the negotiation prompt pin
    price-bearing turns into context even after they scroll out of the window.
    """

    __tablename__ = "vendor_messages"
    __table_args__ = (
        Index("ix_vendor_messages_job_created", "vendor_job_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    vendor_job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("vendor_jobs.id", ondelete="CASCADE"),
        nullable=False,
    )
    # 'ai' | 'vendor' | 'system'
    sender: Mapped[str] = mapped_column(String(10), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    extracted: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # Relationships
    job = relationship(
        "VendorJob", back_populates="messages", foreign_keys=[vendor_job_id]
    )
