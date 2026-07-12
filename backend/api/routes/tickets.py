"""
api/routes/tickets.py

Ticket CRUD endpoints with role-based access and background photo uploads.
"""
from __future__ import annotations

import uuid
import logging

from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from api.deps import CurrentUserDep, DbDep, PMUserDep
from core.storage import upload_file
from database import SessionLocal
from models.property import Property
from models.tenant import Tenant
from models.ticket import Ticket
from schemas.tickets import (
    StatusUpdateResponse,
    TicketCreatedResponse,
    TicketResponse,
    UpdateStatusRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tickets", tags=["tickets"])


# ─── Background Task ─────────────────────────────────────────────────────────


import asyncio
from agentic_AI.ticket_state import TicketState

async def _invoke_graph(state: TicketState, config: dict) -> None:
    from agentic_AI.checkpointer import get_checkpointer
    from agentic_AI.agents.orchestration_agent import get_parent_graph

    with get_checkpointer() as checkpointer:
        graph = get_parent_graph(checkpointer)
        await graph.ainvoke(state.model_dump(), config=config)


async def _resume_approval_graph(ticket_id: uuid.UUID, approved: bool) -> bool:
    """
    Resume the paused approval graph via Command(resume=...) on the ticket's thread.

    Returns True if a live interrupt was resumed, False if there is no paused
    checkpoint to resume (e.g. it was evicted) so the caller can fall back.
    """
    from langgraph.types import Command
    from agentic_AI.checkpointer import get_checkpointer
    from agentic_AI.agents.orchestration_agent import get_parent_graph

    config = {"configurable": {"thread_id": f"ticket-{ticket_id}"}}
    with get_checkpointer() as checkpointer:
        graph = get_parent_graph(checkpointer)
        snapshot = await graph.aget_state(config)
        # `.next` is non-empty only when the graph is paused with pending work
        # (i.e. sitting at the interrupt). Empty ⇒ no live checkpoint to resume.
        if not snapshot or not snapshot.next:
            return False
        await graph.ainvoke(Command(resume={"approved": approved}), config=config)
        return True


def _dispatch_from_db(ticket_id: uuid.UUID) -> None:
    """
    Fallback dispatch when no live checkpoint exists: rebuild TicketState from the
    DB (hydrating `category`, which vendor matching keys off) and run dispatch_graph.
    """
    from agentic_AI.agents.dispatch_agent import dispatch_graph

    db: Session = SessionLocal()
    try:
        ticket: Ticket | None = db.get(Ticket, ticket_id)
        if ticket is None:
            logger.error("Ticket %s not found for fallback dispatch", ticket_id)
            return
        prop: Property | None = db.get(Property, ticket.property_id)
        if prop is None:
            logger.error("Property not found for ticket %s during fallback dispatch", ticket_id)
            return

        state = TicketState(
            ticket_id=str(ticket.id),
            tenant_id=str(ticket.tenant_id),
            property_id=str(ticket.property_id),
            pm_id=str(prop.pm_id),
            category=ticket.category,
            priority=ticket.priority,
            ai_summary=ticket.ai_summary,
            pm_approved=True,
        )
        config = {"configurable": {"thread_id": f"dispatch-{ticket.id}"}}
        asyncio.run(dispatch_graph.ainvoke(state.model_dump(), config=config))
        logger.info("Fallback dispatch completed for ticket %s", ticket_id)
    finally:
        db.close()


def _mark_needs_attention(ticket_id: uuid.UUID) -> None:
    """Surface an unrecoverable approval failure to the PM — never fail silently."""
    db: Session = SessionLocal()
    try:
        ticket: Ticket | None = db.get(Ticket, ticket_id)
        if ticket:
            ticket.status = "NEEDS_ATTENTION"
            db.commit()
    except Exception:
        logger.exception("Failed to mark ticket %s NEEDS_ATTENTION", ticket_id)
    finally:
        db.close()


def _run_approval(ticket_id: uuid.UUID) -> None:
    """
    Background task for PM approval: resume the paused graph; if the checkpoint is
    gone, fall back to a fresh DB-based dispatch. Escalate on unrecoverable failure.
    """
    try:
        resumed = asyncio.run(_resume_approval_graph(ticket_id, approved=True))
        if resumed:
            logger.info("Resumed approval graph for ticket %s", ticket_id)
            return
        logger.warning("No live checkpoint for ticket %s — falling back to DB dispatch", ticket_id)
        _dispatch_from_db(ticket_id)
    except Exception:
        logger.exception("Approval processing failed for ticket %s", ticket_id)
        _mark_needs_attention(ticket_id)

def _process_ticket_submission(
    ticket_id: uuid.UUID,
    file_contents: list[tuple[bytes, str, str]],
) -> None:
    """
    Background task that:
    1. Uploads each photo to Supabase Storage.
    2. Updates the ticket with media_urls.
    3. Triggers LangGraph orchestration workflow.

    Runs in its own DB session (independent of the request lifecycle).
    """
    db: Session = SessionLocal()
    try:
        media_urls: list[str] = []

        for file_bytes, filename, content_type in file_contents:
            try:
                url = upload_file(
                    file_bytes=file_bytes,
                    original_filename=filename,
                    ticket_id=ticket_id,
                    content_type=content_type,
                )
                media_urls.append(url)
            except Exception:
                logger.exception("Failed to upload file %s for ticket %s", filename, ticket_id)

        ticket: Ticket | None = db.get(Ticket, ticket_id)
        if ticket is None:
            logger.error("Ticket %s not found during background processing", ticket_id)
            return

        ticket.media_urls = media_urls if media_urls else None
        db.commit()

        # Build initial state and trigger graph
        prop: Property | None = db.get(Property, ticket.property_id)
        if not prop:
            logger.error("Property not found for ticket %s", ticket_id)
            return

        initial_state = TicketState(
            ticket_id=str(ticket.id),
            tenant_id=str(ticket.tenant_id),
            property_id=str(ticket.property_id),
            pm_id=str(prop.pm_id),
        )
        config = {"configurable": {"thread_id": f"ticket-{ticket.id}"}}
        
        asyncio.run(_invoke_graph(initial_state, config))
        logger.info("Graph completed for ticket %s", ticket_id)

    except Exception:
        db.rollback()
        logger.exception("Background processing failed for ticket %s", ticket_id)
        try:
            # Reopen session state handle to update error state safely
            err_ticket = db.get(Ticket, ticket_id)
            if err_ticket:
                err_ticket.status = "ERROR"
                db.commit()
        except:
            pass
    finally:
        db.close()

# ─── Endpoints ────────────────────────────────────────────────────────────────


@router.post(
    "",
    response_model=TicketCreatedResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def create_ticket(
    background_tasks: BackgroundTasks,
    user: CurrentUserDep,
    db: DbDep,
    title: str = Form(...),
    description: str = Form(None),
    permission_to_enter: bool = Form(False),
    photos: list[UploadFile] = File(default=[]),
) -> TicketCreatedResponse:
    """
    Submit a new maintenance ticket.

    - Only tenants may create tickets.
    - Photos are uploaded to Supabase in the background.
    - Returns immediately with the new ticket ID.
    """
    # ── RBAC: only tenants can create tickets ──
    if user.role != "tenant":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only tenants can create tickets.",
        )

    # ── Resolve tenant profile and property ──
    tenant: Tenant | None = (
        db.query(Tenant)
        .filter(Tenant.user_id == user.id, Tenant.is_active.is_(True))
        .first()
    )
    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant profile not found.",
        )

    # ── Read file bytes while the request is still alive ──
    file_contents: list[tuple[bytes, str, str]] = []
    for photo in photos:
        content = photo.file.read()
        file_contents.append((content, photo.filename or "photo.jpg", photo.content_type or "image/jpeg"))

    # ── Create skeleton ticket ──
    ticket_id = uuid.uuid4()
    ticket = Ticket(
        id=ticket_id,
        property_id=tenant.property_id,
        tenant_id=tenant.id,
        title=title,
        description=description,
        permission_to_enter=permission_to_enter,
        status="PENDING_UPLOAD" if file_contents else "OPEN",
    )
    db.add(ticket)
    db.commit()

    # ── Schedule background upload (only if there are files) ──
    if file_contents:
        background_tasks.add_task(_process_ticket_submission, ticket_id, file_contents)

    return TicketCreatedResponse(id=ticket_id)


@router.get("", response_model=list[TicketResponse])
def list_tickets(
    user: CurrentUserDep,
    db: DbDep,
    property_id: uuid.UUID | None = None,
    ticket_status: str | None = None,
    category: str | None = None,
) -> list[TicketResponse]:
    """
    List tickets based on user role.

    - **Tenant**: sees only their own tickets.
    - **PM**: sees tickets for all owned properties; supports optional filters.
    """
    if user.role == "tenant":
        tenant: Tenant | None = (
            db.query(Tenant).filter(Tenant.user_id == user.id).first()
        )
        if tenant is None:
            return []

        query = db.query(Ticket).filter(Ticket.tenant_id == tenant.id)

    elif user.role == "pm":
        # Get all property IDs belonging to this PM
        pm_property_ids = [
            p.id for p in db.query(Property).filter(Property.pm_id == user.id).all()
        ]
        if not pm_property_ids:
            return []

        query = db.query(Ticket).filter(Ticket.property_id.in_(pm_property_ids))

        if property_id is not None:
            if property_id not in pm_property_ids:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Property does not belong to you.",
                )
            query = query.filter(Ticket.property_id == property_id)

        if ticket_status is not None:
            query = query.filter(Ticket.status == ticket_status)

        if category is not None:
            query = query.filter(Ticket.category == category)

    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied.",
        )

    tickets = query.order_by(Ticket.created_at.desc()).all()
    return [TicketResponse.model_validate(t) for t in tickets]


@router.get("/{ticket_id}", response_model=TicketResponse)
def get_ticket(
    ticket_id: uuid.UUID,
    user: CurrentUserDep,
    db: DbDep,
) -> TicketResponse:
    """
    Get a single ticket by ID.

    - Tenant: must own the ticket.
    - PM: ticket must belong to one of their properties.
    """
    ticket: Ticket | None = db.get(Ticket, ticket_id)
    if ticket is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found.",
        )

    if user.role == "tenant":
        tenant: Tenant | None = (
            db.query(Tenant).filter(Tenant.user_id == user.id).first()
        )
        if tenant is None or ticket.tenant_id != tenant.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have access to this ticket.",
            )

    elif user.role == "pm":
        prop: Property | None = db.get(Property, ticket.property_id)
        if prop is None or prop.pm_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This ticket does not belong to your properties.",
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied.",
        )

    return TicketResponse.model_validate(ticket)


@router.patch("/{ticket_id}/status", response_model=StatusUpdateResponse)
def update_ticket_status(
    ticket_id: uuid.UUID,
    body: UpdateStatusRequest,
    pm: PMUserDep,
    db: DbDep,
) -> StatusUpdateResponse:
    """
    Update a ticket's status. PM only.

    Validates that the ticket belongs to one of the PM's properties.
    """
    ticket: Ticket | None = db.get(Ticket, ticket_id)
    if ticket is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found.",
        )

    # Verify ownership through property
    prop: Property | None = db.get(Property, ticket.property_id)
    if prop is None or prop.pm_id != pm.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This ticket does not belong to your properties.",
        )

    ticket.status = body.status
    db.commit()
    db.refresh(ticket)

    return StatusUpdateResponse(id=ticket.id, status=ticket.status)


@router.post("/{ticket_id}/approve", response_model=StatusUpdateResponse, status_code=status.HTTP_202_ACCEPTED)
def approve_ticket(
    ticket_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    pm: PMUserDep,
    db: DbDep,
) -> StatusUpdateResponse:
    """
    PM approves a ticket, triggering vendor dispatch in the background.

    Used for P2/P3/P4 tickets sitting at PENDING_APPROVAL (P1 auto-dispatches
    during intake and never reaches here).
    """
    ticket: Ticket | None = db.get(Ticket, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found.")

    prop: Property | None = db.get(Property, ticket.property_id)
    if prop is None or prop.pm_id != pm.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This ticket does not belong to your properties.",
        )

    # Guard: only a ticket actually awaiting approval may be approved. Prevents a
    # re-approve from resuming/dispatching an already-processed ticket.
    if ticket.status != "PENDING_APPROVAL":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Ticket is not awaiting approval (status: {ticket.status}).",
        )

    ticket.status = "DISPATCHING"
    db.commit()
    db.refresh(ticket)

    background_tasks.add_task(_run_approval, ticket_id)

    return StatusUpdateResponse(id=ticket.id, status=ticket.status)


@router.post("/{ticket_id}/reject", response_model=StatusUpdateResponse)
def reject_ticket(
    ticket_id: uuid.UUID,
    pm: PMUserDep,
    db: DbDep,
) -> StatusUpdateResponse:
    """
    PM rejects a ticket — no dispatch, ticket is cancelled.

    A terminal state-set, written synchronously here rather than routed through
    the graph — it must not depend on a live checkpoint. The paused graph is left
    to expire via its TTL; the PENDING_APPROVAL guard makes it unresumable anyway.
    """
    ticket: Ticket | None = db.get(Ticket, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found.")

    prop: Property | None = db.get(Property, ticket.property_id)
    if prop is None or prop.pm_id != pm.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This ticket does not belong to your properties.",
        )

    if ticket.status != "PENDING_APPROVAL":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Ticket is not awaiting approval (status: {ticket.status}).",
        )

    ticket.status = "CANCELLED"
    db.commit()
    db.refresh(ticket)

    return StatusUpdateResponse(id=ticket.id, status=ticket.status)
