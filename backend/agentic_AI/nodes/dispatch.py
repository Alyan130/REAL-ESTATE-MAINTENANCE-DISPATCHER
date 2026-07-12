"""
backend/agentic_AI/nodes/dispatch.py

Dispatch agent graph nodes. Given a ticket that is ready to act on (P1 auto, or
PM-approved), select the single best vendor, create a VendorJob, and email the
job offer. If no vendor fits, escalate to the PM.

Node convention (mirrors nodes/intake.py): each node is
`async def node(state) -> dict`, opens its own SessionLocal, wraps its body in
try/except → logger.exception + `{"error": ...}`, closes in finally, and returns
only the state keys it changed.
"""
import logging
import uuid
from datetime import datetime
from typing import Any, Dict

from core.email import send_job_offer_email
from database import SessionLocal
from models.notification import Notification
from models.ticket import Ticket
from models.vendor import Vendor
from agentic_AI.ticket_state import TicketState
from agentic_AI.tools.dispatch import create_vendor_job, find_best_vendor

logger = logging.getLogger(__name__)


async def select_vendor_node(state: TicketState) -> Dict[str, Any]:
    """Pick the best eligible vendor and stash its id on the state."""
    if state.category is None:
        logger.warning("select_vendor_node: category missing for ticket %s", state.ticket_id)
        return {"error": "category missing — cannot dispatch"}

    db = SessionLocal()
    try:
        vendor = find_best_vendor(
            db,
            pm_id=uuid.UUID(state.pm_id),
            category=state.category,
            ticket_id=uuid.UUID(state.ticket_id),
        )
        if vendor is None:
            logger.info(
                "select_vendor_node: no eligible vendor for ticket %s (%s)",
                state.ticket_id,
                state.category,
            )
            return {}  # leaves assigned_vendor_id None → routes to escalate
        return {"assigned_vendor_id": str(vendor.id)}
    except Exception as e:
        logger.exception("select_vendor_node error for %s: %s", state.ticket_id, e)
        return {"error": str(e)}
    finally:
        db.close()


def route_after_selection(state: TicketState) -> str:
    """Route to dispatch if a vendor was found, otherwise escalate to the PM."""
    if state.error is not None:
        return "escalate"
    if state.assigned_vendor_id:
        return "dispatch_job"
    return "escalate"


async def dispatch_job_node(state: TicketState) -> Dict[str, Any]:
    """Create the VendorJob, email the vendor, mark the ticket DISPATCHED."""
    db = SessionLocal()
    try:
        create_vendor_job(
            db,
            ticket_id=uuid.UUID(state.ticket_id),
            vendor_id=uuid.UUID(state.assigned_vendor_id),
        )

        vendor = db.get(Vendor, uuid.UUID(state.assigned_vendor_id))
        ticket = db.get(Ticket, state.ticket_id)
        if ticket is None:
            return {"error": "ticket not found"}

        # Fire-and-forget email — a failure must not roll back the created job.
        if vendor and vendor.email:
            send_job_offer_email(
                to_email=vendor.email,
                vendor_name=vendor.name,
                ticket_title=ticket.title,
                ticket_summary=ticket.ai_summary or ticket.description or "",
                ticket_id=state.ticket_id,
            )
        else:
            logger.warning(
                "dispatch_job_node: vendor %s has no email; skipping offer for ticket %s",
                state.assigned_vendor_id,
                state.ticket_id,
            )

        ticket.status = "DISPATCHED"
        ticket.updated_at = datetime.utcnow()
        db.commit()

        return {
            "vendors_contacted": [state.assigned_vendor_id],
            "dispatch_attempts": 1,
            "current_status": "DISPATCHED",
        }
    except Exception as e:
        db.rollback()
        logger.exception("dispatch_job_node error for %s: %s", state.ticket_id, e)
        return {"error": str(e)}
    finally:
        db.close()


async def escalate_to_pm_node(state: TicketState) -> Dict[str, Any]:
    """No vendor available (or category is 'other') — notify the PM and flag the ticket."""
    db = SessionLocal()
    try:
        notification = Notification(
            id=uuid.uuid4(),
            user_id=uuid.UUID(state.pm_id),
            type="NO_VENDOR_AVAILABLE",
            title="No vendor available",
            message=f"Ticket needs a {state.category or 'maintenance'} vendor — none available. Please assign one manually.",
            is_read=False,
        )
        db.add(notification)

        ticket = db.get(Ticket, state.ticket_id)
        if ticket:
            ticket.status = "NEEDS_ATTENTION"
            ticket.updated_at = datetime.utcnow()

        db.commit()
        return {"current_status": "NEEDS_ATTENTION"}
    except Exception as e:
        db.rollback()
        logger.exception("escalate_to_pm_node error for %s: %s", state.ticket_id, e)
        return {"error": str(e)}
    finally:
        db.close()
