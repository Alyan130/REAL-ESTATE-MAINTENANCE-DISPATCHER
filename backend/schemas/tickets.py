"""
schemas/tickets.py

Pydantic models for maintenance ticket endpoints.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel


class TicketCreatedResponse(BaseModel):
    id: uuid.UUID
    message: str = "Ticket received. Processing in background."


class TicketResponse(BaseModel):
    id: uuid.UUID
    property_id: uuid.UUID
    tenant_id: u
    uid.UUID
    title: str
    description: str | None
    category: str | None
    priority: str | None
    status: str
    media_urls: list[str] | None
    ai_summary: str | None
    permission_to_enter: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class UpdateStatusRequest(BaseModel):
    status: str


class StatusUpdateResponse(BaseModel):
    id: uuid.UUID
    status: str
