"""
schemas/categories.py

Pydantic models for the PM's category vocabulary and pricing.

- CreateCategoryRequest : body for POST /categories
- UpdateCategoryRequest : body for PATCH /categories/{id}, every field optional
- CategoryResponse      : used by every category endpoint

`target_price` and `max_price` are what the negotiation agent reads: the anchor
it negotiates toward, and the ceiling below which a quote is auto-approved.
"""
from __future__ import annotations

import uuid
from decimal import Decimal

from pydantic import BaseModel, Field, model_validator


class CreateCategoryRequest(BaseModel):
    label: str = Field(min_length=1, max_length=60)
    # Slugified from `label` when omitted.
    name: str | None = Field(default=None, max_length=60)
    target_price: Decimal | None = Field(default=None, ge=0, le=1_000_000)
    max_price: Decimal | None = Field(default=None, ge=0, le=1_000_000)

    @model_validator(mode="after")
    def _ceiling_not_below_anchor(self) -> "CreateCategoryRequest":
        if (
            self.target_price is not None
            and self.max_price is not None
            and self.max_price < self.target_price
        ):
            raise ValueError("max_price cannot be below target_price")
        return self


class UpdateCategoryRequest(BaseModel):
    """Every field optional — a PATCH that only sets a price leaves the rest alone.

    Prices are deliberately nullable: clearing `max_price` is how a PM turns
    auto-approval back off for a category.
    """

    label: str | None = Field(default=None, min_length=1, max_length=60)
    target_price: Decimal | None = Field(default=None, ge=0, le=1_000_000)
    max_price: Decimal | None = Field(default=None, ge=0, le=1_000_000)
    sort_order: int | None = Field(default=None, ge=0)


class CategoryResponse(BaseModel):
    id: uuid.UUID
    name: str
    label: str
    target_price: float | None
    max_price: float | None
    is_vendor_selectable: bool
    sort_order: int

    model_config = {"from_attributes": True}
