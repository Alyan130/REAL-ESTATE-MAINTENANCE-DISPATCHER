"""
app/api/v1/categories.py

The PM's maintenance vocabulary and pricing. Every route is PM-scoped: a PM only
ever sees and edits their own categories.

These rows are the agents' configuration surface — intake classifies into them,
and the negotiation agent reads their prices — so this router is effectively how
a PM tunes the AI's behaviour.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Query, status

from app.dependencies import CategoryServiceDep, PMUserDep
from app.schemas.categories import (
    CategoryResponse,
    CreateCategoryRequest,
    UpdateCategoryRequest,
)

router = APIRouter(prefix="/categories", tags=["categories"])


@router.get("/", response_model=list[CategoryResponse])
def list_categories(
    pm: PMUserDep,
    service: CategoryServiceDep,
    vendor_selectable_only: bool = Query(
        False,
        description="Exclude 'other', which is the intake fallback and never a vendor specialty.",
    ),
) -> list[CategoryResponse]:
    """List the PM's active categories, seeding the starter set on first call."""
    return service.list_for_pm(pm.id, vendor_selectable_only=vendor_selectable_only)


@router.post("/", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
def create_category(
    data: CreateCategoryRequest,
    pm: PMUserDep,
    service: CategoryServiceDep,
) -> CategoryResponse:
    """Add a category. The slug is derived from the label unless one is given."""
    return service.create(pm.id, data)


@router.patch("/{category_id}", response_model=CategoryResponse)
def update_category(
    category_id: uuid.UUID,
    data: UpdateCategoryRequest,
    pm: PMUserDep,
    service: CategoryServiceDep,
) -> CategoryResponse:
    """Update a category's label, prices, or position.

    Clearing `max_price` turns auto-approval off for the category; the slug
    itself is never renamed, since past tickets reference it by value.
    """
    return service.update(category_id, pm.id, data)


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(
    category_id: uuid.UUID,
    pm: PMUserDep,
    service: CategoryServiceDep,
) -> None:
    """Soft-delete a category. 'Other' is protected — intake escalation needs it."""
    service.deactivate(category_id, pm.id)
