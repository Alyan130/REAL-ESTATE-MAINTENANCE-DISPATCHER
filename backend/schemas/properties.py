"""
schemas/properties.py

Pydantic models for property CRUD endpoints.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel


class CreatePropertyRequest(BaseModel):
    name: str
    address: str


class PropertyResponse(BaseModel):
    id: uuid.UUID
    pm_id: uuid.UUID
    name: str
    address: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}
