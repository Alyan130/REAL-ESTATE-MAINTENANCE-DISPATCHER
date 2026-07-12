"""
backend/agentic_AI/tools/dispatch.py

Reusable workers for the Dispatch agent — vendor selection and VendorJob
creation. Nodes orchestrate; these do the DB work.

Vendor selection is deterministic (filter + rank by rating), not an LLM call:
the only ranking signal on a vendor is `rating`, so a SQL sort beats a model
call that has the same single number to reason over.
"""
from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from models.vendor import Vendor
from models.vendor_job import VendorJob

# Statuses that count against a vendor's concurrent-job capacity.
ACTIVE_JOB_STATUSES = ["PENDING", "APPROVED"]


def find_best_vendor(
    db: Session,
    pm_id: uuid.UUID,
    category: str,
    ticket_id: uuid.UUID,
) -> Vendor | None:
    """
    Return the single best-matching vendor for a ticket, or None.

    A vendor qualifies when it is the PM's, active, services the category, has
    not already been contacted for THIS ticket, and has free capacity. Ranked
    by rating (highest first).

    Exclusion is driven by the VendorJob table (a row per contacted vendor), not
    by graph state — the table is authoritative and survives across the separate
    graph invocations that the P1 and PM-approval paths use.
    """
    # Vendors already contacted for this ticket (authoritative exclusion).
    contacted_rows = (
        db.query(VendorJob.vendor_id)
        .filter(VendorJob.ticket_id == ticket_id)
        .all()
    )
    contacted_ids = [row[0] for row in contacted_rows]

    query = (
        db.query(Vendor)
        .filter(
            Vendor.pm_id == pm_id,
            Vendor.is_active.is_(True),
            Vendor.categories.any(category),  # category = ANY(vendors.categories)
        )
    )
    if contacted_ids:
        query = query.filter(~Vendor.id.in_(contacted_ids))

    candidates = query.order_by(Vendor.rating.desc()).all()

    # Return the highest-rated candidate that still has capacity.
    for vendor in candidates:
        active_jobs = (
            db.query(VendorJob)
            .filter(
                VendorJob.vendor_id == vendor.id,
                VendorJob.status.in_(ACTIVE_JOB_STATUSES),
            )
            .count()
        )
        if active_jobs < vendor.max_concurrent_jobs:
            return vendor

    return None


def create_vendor_job(
    db: Session,
    ticket_id: uuid.UUID,
    vendor_id: uuid.UUID,
) -> VendorJob:
    """
    Create a PENDING VendorJob linking a ticket to the selected vendor.

    The row itself is the record that this vendor was contacted for this ticket.
    """
    job = VendorJob(
        id=uuid.uuid4(),
        ticket_id=ticket_id,
        vendor_id=vendor_id,
        status="PENDING",
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job
