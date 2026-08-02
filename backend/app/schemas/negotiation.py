"""
app/schemas/negotiation.py

Wire shapes for the vendor chat and the PM's decision card.

The vendor-facing and PM-facing views of the same negotiation are deliberately
different objects. The vendor sees the job and the transcript; the PM also sees
the quote, the ceiling, and the suggested counter. Sharing one schema would make
it far too easy to leak the PM's ceiling to the vendor's unauthenticated page.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class MessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    sender: str  # ai | vendor | system
    body: str
    created_at: datetime


class VendorChatResponse(BaseModel):
    """
    What the vendor sees on the token-gated page.

    Note what is absent: the street address, the PM's ceiling, the target price,
    and any other vendor's quote. This page is reachable by anyone holding a
    forwarded link, so it carries only what is needed to quote the work.
    """

    vendor_job_id: uuid.UUID
    vendor_name: str
    ticket_title: str
    ticket_summary: str
    category_label: str
    priority_label: str
    property_label: str  # name only — never the address until APPROVED
    access_note: str
    media_urls: list[str] = Field(default_factory=list)
    status: str
    can_reply: bool
    messages: list[MessageResponse] = Field(default_factory=list)


class PostMessageRequest(BaseModel):
    body: str = Field(min_length=1, max_length=4000)


class MessageAcceptedResponse(BaseModel):
    """202: the message is stored; the AI's answer arrives on a later poll."""

    id: uuid.UUID
    created_at: datetime


class NegotiationResponse(BaseModel):
    """The PM's decision card."""

    vendor_job_id: uuid.UUID
    vendor_name: str
    vendor_rating: float | None = None
    status: str
    quoted_price: Decimal | None = None
    availability: str | None = None
    target_price: Decimal | None = None
    max_price: Decimal | None = None
    suggested_counter: Decimal | None = None
    decision_reason: str | None = None
    counter_rounds_used: int = 0
    counter_allowed: bool = True
    awaiting_decision: bool = False
    messages: list[MessageResponse] = Field(default_factory=list)


class NegotiationDecisionRequest(BaseModel):
    action: str = Field(description="accept | counter | next_vendor")
    counter_price: Decimal | None = Field(
        default=None, description="required when action is 'counter'"
    )


class NegotiationDecisionResponse(BaseModel):
    vendor_job_id: uuid.UUID
    action: str
