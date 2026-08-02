"""
app/api/v1/negotiations.py

The PM's side of a negotiation: read the thread, and decide on the quote.

Mounted under /tickets so the negotiation reads as part of the ticket it belongs
to, which is also how the frontend loads it.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, BackgroundTasks, status

from app.dependencies import NegotiationServiceDep, PMUserDep
from app.schemas.negotiation import (
    NegotiationDecisionRequest,
    NegotiationDecisionResponse,
    NegotiationResponse,
)

router = APIRouter(prefix="/tickets", tags=["negotiations"])


@router.get("/{ticket_id}/negotiation", response_model=NegotiationResponse)
def get_negotiation(
    ticket_id: uuid.UUID,
    pm: PMUserDep,
    service: NegotiationServiceDep,
) -> NegotiationResponse:
    """
    The live negotiation for this ticket, with the quote and a suggested counter.

    404s when there is no negotiation — the frontend loads this separately from
    the ticket itself precisely so that 404 doesn't blank the page.
    """
    return service.get_for_ticket(ticket_id, pm.id)


@router.post(
    "/{ticket_id}/negotiation/decision",
    response_model=NegotiationDecisionResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def decide(
    ticket_id: uuid.UUID,
    data: NegotiationDecisionRequest,
    pm: PMUserDep,
    service: NegotiationServiceDep,
    background_tasks: BackgroundTasks,
) -> NegotiationDecisionResponse:
    """
    Accept the quote, counter it once, or move to the next vendor.

    Validated synchronously and the job status flipped before returning, so a
    double-click 409s rather than scheduling the work twice.
    """
    return service.decide(
        ticket_id,
        pm.id,
        data.action,
        data.counter_price,
        background_tasks.add_task,
    )
