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

from app.database import SessionLocal
from app.models.notification import Notification
from app.models.ticket import Ticket
from app.agentic_AI.ticket_state import TicketState
from app.agentic_AI.tools.dispatch import create_vendor_job, find_best_vendor

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
    """
    Create the VendorJob and mark the ticket DISPATCHED.

    The offer email is deliberately NOT sent here. It carries the tokenized chat
    link, and the token can only be minted once the job row exists — so
    `open_negotiation` (the next node) owns both, and owns them together. Sending
    from both places would mail the vendor twice.
    """
    db = SessionLocal()
    try:
        job = create_vendor_job(
            db,
            ticket_id=uuid.UUID(state.ticket_id),
            vendor_id=uuid.UUID(state.assigned_vendor_id),
        )

        ticket = db.get(Ticket, state.ticket_id)
        if ticket is None:
            return {"error": "ticket not found"}

        ticket.status = "DISPATCHED"
        ticket.updated_at = datetime.utcnow()
        db.commit()

        return {
            "active_vendor_job_id": str(job.id),
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
