"""
app/services/ticket_service.py

Ticket lifecycle, and the background work that carries it.

Two things run outside the request here — photo upload plus AI classification,
and PM approval plus vendor dispatch. Both are module-level functions with their
own `SessionLocal()`, because a request-scoped session is closed long before they
finish.
"""
from __future__ import annotations

import logging
import uuid
from typing import Callable, Protocol

from sqlalchemy.orm import Session

from app.agentic_AI.runtime import run_async
from app.agentic_AI.ticket_state import TicketState
from app.agentic_AI.tracing import STAGE_DISPATCH, STAGE_INTAKE, trace_config
from app.core.storage import upload_file
from app.database import SessionLocal
from app.exceptions import ForbiddenError, NotFoundError, TicketNotAwaitingApprovalError
from app.models.property import Property
from app.models.ticket import Ticket
from app.models.user import User
from app.repositories.property_repo import PropertyRepository
from app.repositories.tenant_repo import TenantRepository
from app.repositories.ticket_repo import TicketRepository
from app.schemas.tickets import StatusUpdateResponse, TicketCreatedResponse, TicketResponse
from app.services.base import BaseService

logger = logging.getLogger(__name__)

# (bytes, filename, content_type) — read while the request is still alive, since
# the UploadFile stream is gone by the time the background task runs.
UploadedFile = tuple[bytes, str, str]


class TaskScheduler(Protocol):
    """`BackgroundTasks.add_task`, narrowed so this module imports no FastAPI."""

    def __call__(self, func: Callable[..., object], /, *args: object) -> object: ...


# ─── Background work ─────────────────────────────────────────────────────────


async def _invoke_graph(state: TicketState, config: dict) -> None:
    from app.agentic_AI.agents.orchestration_agent import get_parent_graph
    from app.agentic_AI.checkpointer import get_checkpointer

    async with get_checkpointer() as checkpointer:
        graph = get_parent_graph(checkpointer)
        await graph.ainvoke(state.model_dump(), config=config)


async def _resume_approval_graph(ticket_id: uuid.UUID, approved: bool) -> bool:
    """
    Resume the paused approval graph via Command(resume=...) on the ticket's thread.

    Returns True if a live interrupt was resumed, False if there is no paused
    checkpoint to resume (e.g. it was evicted) so the caller can fall back.
    """
    from langgraph.types import Command

    from app.agentic_AI.agents.orchestration_agent import get_parent_graph
    from app.agentic_AI.checkpointer import get_checkpointer

    config = trace_config(
        f"ticket-{ticket_id}",
        stage=STAGE_DISPATCH,
        run_name=f"pm-{'approve' if approved else 'reject'}:{ticket_id}",
        ticket_id=str(ticket_id),
        pm_decision="approved" if approved else "rejected",
    )
    async with get_checkpointer() as checkpointer:
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
    Fallback dispatch when no live checkpoint exists: rebuild TicketState from
    the DB (hydrating `category`, which vendor matching keys off) and run
    dispatch → negotiate.

    This runs the **post-approval** graph, not `dispatch_graph`. Negotiation
    contains `interrupt()` calls, which raise without a checkpointer — and
    `dispatch_graph` is compiled without one on purpose. Running bare dispatch
    here would leave the ticket at DISPATCHED with a vendor who was never
    contacted, silently, on the one path that only runs when something already
    went wrong.

    The thread is namespaced by attempt number so the next-vendor loop gets a
    fresh thread each time rather than colliding with a completed one.
    """
    from app.agentic_AI.agents.orchestration_agent import get_post_approval_graph
    from app.agentic_AI.checkpointer import get_checkpointer
    from app.models.vendor_job import VendorJob

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

        attempt = (
            db.query(VendorJob).filter(VendorJob.ticket_id == ticket_id).count()
        )
        thread_id = f"dispatch-{ticket.id}-{attempt}"

        state = TicketState(
            ticket_id=str(ticket.id),
            tenant_id=str(ticket.tenant_id),
            property_id=str(ticket.property_id),
            pm_id=str(prop.pm_id),
            category=ticket.category,
            priority=ticket.priority,
            ai_summary=ticket.ai_summary,
            pm_approved=True,
            negotiation_thread_id=thread_id,
        )
        config = trace_config(
            thread_id,
            stage=STAGE_DISPATCH,
            run_name=f"dispatch-fallback:{ticket.id}",
            ticket_id=str(ticket.id),
            pm_id=str(prop.pm_id),
            priority=ticket.priority,
            attempt=attempt,
            # This path only runs when the checkpoint was already lost, so mark
            # it — a run list full of these means the TTL is too short.
            fallback=True,
        )

        async def _run() -> None:
            async with get_checkpointer() as checkpointer:
                graph = get_post_approval_graph(checkpointer)
                await graph.ainvoke(state.model_dump(), config=config)

        run_async(_run())
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


def run_approval(ticket_id: uuid.UUID) -> None:
    """
    Background task for PM approval: resume the paused graph; if the checkpoint is
    gone, fall back to a fresh DB-based dispatch. Escalate on unrecoverable failure.
    """
    try:
        resumed = run_async(_resume_approval_graph(ticket_id, approved=True))
        if resumed:
            logger.info("Resumed approval graph for ticket %s", ticket_id)
            return

        logger.warning("No live checkpoint for ticket %s — falling back to DB dispatch", ticket_id)
        _dispatch_from_db(ticket_id)
    except Exception:
        logger.exception("Approval processing failed for ticket %s", ticket_id)
        _mark_needs_attention(ticket_id)


def process_ticket_submission(
    ticket_id: uuid.UUID,
    file_contents: list[UploadedFile],
) -> None:
    """
    Background task that:
    1. Uploads each photo to Supabase Storage.
    2. Updates the ticket with media_urls.
    3. Triggers the LangGraph orchestration workflow.
    """
    db: Session = SessionLocal()
    try:
        media_urls: list[str] = []

        for file_bytes, filename, content_type in file_contents:
            try:
                media_urls.append(
                    upload_file(
                        file_bytes=file_bytes,
                        original_filename=filename,
                        ticket_id=ticket_id,
                        content_type=content_type,
                    )
                )
            except Exception:
                # One bad photo must not cost the ticket its classification.
                logger.exception("Failed to upload file %s for ticket %s", filename, ticket_id)

        ticket: Ticket | None = db.get(Ticket, ticket_id)
        if ticket is None:
            logger.error("Ticket %s not found during background processing", ticket_id)
            return

        ticket.media_urls = media_urls if media_urls else None
        db.commit()

        prop: Property | None = db.get(Property, ticket.property_id)
        if not prop:
            logger.error("Property not found for ticket %s", ticket_id)
            return

        thread_id = f"ticket-{ticket.id}"
        config = trace_config(
            thread_id,
            stage=STAGE_INTAKE,
            run_name=f"ticket-submission:{ticket.id}",
            ticket_id=str(ticket.id),
            pm_id=str(prop.pm_id),
        )
        initial_state = TicketState(
            ticket_id=str(ticket.id),
            tenant_id=str(ticket.tenant_id),
            property_id=str(ticket.property_id),
            pm_id=str(prop.pm_id),
            # Carried in state so `open_negotiation` can mirror it onto the
            # VendorJob row — a later resume then looks the thread up rather
            # than reconstructing a naming convention.
            negotiation_thread_id=thread_id,
        )

        run_async(_invoke_graph(initial_state, config))
        logger.info("Graph completed for ticket %s", ticket_id)

    except Exception:
        db.rollback()
        logger.exception("Background processing failed for ticket %s", ticket_id)
        try:
            err_ticket = db.get(Ticket, ticket_id)
            if err_ticket:
                err_ticket.status = "ERROR"
                db.commit()
        except Exception:
            logger.exception("Could not mark ticket %s as ERROR", ticket_id)
    finally:
        db.close()


# ─── Service ─────────────────────────────────────────────────────────────────


class TicketService(BaseService):
    def __init__(self, db: Session) -> None:
        super().__init__(db)
        self.tickets = TicketRepository(db)
        self.tenants = TenantRepository(db)
        self.properties = PropertyRepository(db)

    def create(
        self,
        user: User,
        title: str,
        description: str | None,
        permission_to_enter: bool,
        files: list[UploadedFile],
        schedule: TaskScheduler,
    ) -> TicketCreatedResponse:
        """
        Write the ticket and hand the slow half off to the background.

        Returns as soon as the row exists so the tenant isn't held on a spinner
        while photos upload and the AI classifies.
        """
        tenant = self.tenants.get_active_by_user_id(user.id)
        if tenant is None:
            raise NotFoundError("Tenant profile not found.")

        ticket_id = uuid.uuid4()
        self.tickets.add(
            Ticket(
                id=ticket_id,
                property_id=tenant.property_id,
                tenant_id=tenant.id,
                title=title,
                description=description,
                permission_to_enter=permission_to_enter,
                status="PENDING_UPLOAD" if files else "OPEN",
            )
        )
        self._commit()

        # Note: with no photos the ticket stays OPEN and no graph runs, so it is
        # never classified. Pre-existing behaviour, preserved deliberately.
        if files:
            schedule(process_ticket_submission, ticket_id, files)

        return TicketCreatedResponse(id=ticket_id)

    def list_for_user(
        self,
        user: User,
        property_id: uuid.UUID | None = None,
        status: str | None = None,
        category: str | None = None,
    ) -> list[TicketResponse]:
        """A tenant sees only their own; a PM sees every property they own."""
        if user.role == "tenant":
            tenant = self.tenants.get_any_by_user_id(user.id)
            if tenant is None:
                return []
            tickets = self.tickets.list_for_tenant(tenant.id)

        elif user.role == "pm":
            owned_ids = self.properties.list_active_ids_for_pm(user.id)
            if not owned_ids:
                return []

            if property_id is not None and property_id not in owned_ids:
                raise ForbiddenError("Property does not belong to you.")

            tickets = self.tickets.list_for_properties(
                owned_ids, property_id=property_id, status=status, category=category
            )

        else:
            raise ForbiddenError("Access denied.")

        return [TicketResponse.model_validate(ticket) for ticket in tickets]

    def get_for_user(self, ticket_id: uuid.UUID, user: User) -> TicketResponse:
        ticket = self._ticket_or_404(ticket_id)

        if user.role == "tenant":
            tenant = self.tenants.get_any_by_user_id(user.id)
            if tenant is None or ticket.tenant_id != tenant.id:
                raise ForbiddenError("You do not have access to this ticket.")

        elif user.role == "pm":
            self._require_pm_owns(ticket, user.id)

        else:
            raise ForbiddenError("Access denied.")

        return TicketResponse.model_validate(ticket)

    def update_status(
        self, ticket_id: uuid.UUID, pm_id: uuid.UUID, status: str
    ) -> StatusUpdateResponse:
        """Manual override. Writes the status directly, skipping the workflow."""
        ticket = self._ticket_or_404(ticket_id)
        self._require_pm_owns(ticket, pm_id)

        ticket.status = status
        self._commit()
        self.db.refresh(ticket)

        return StatusUpdateResponse(id=ticket.id, status=ticket.status)

    def approve(
        self, ticket_id: uuid.UUID, pm_id: uuid.UUID, schedule: TaskScheduler
    ) -> StatusUpdateResponse:
        """
        Approve and hand off to vendor dispatch.

        Answers immediately with DISPATCHING; the settled result (DISPATCHED or
        NEEDS_ATTENTION) is written by the background task seconds later.
        """
        ticket = self._require_awaiting_approval(ticket_id, pm_id)

        ticket.status = "DISPATCHING"
        self._commit()
        self.db.refresh(ticket)

        schedule(run_approval, ticket_id)

        return StatusUpdateResponse(id=ticket.id, status=ticket.status)

    def reject(self, ticket_id: uuid.UUID, pm_id: uuid.UUID) -> StatusUpdateResponse:
        """
        Terminal, and written synchronously rather than routed through the graph —
        it must not depend on a live checkpoint. The paused graph expires via its
        TTL, and the PENDING_APPROVAL guard makes it unresumable anyway.
        """
        ticket = self._require_awaiting_approval(ticket_id, pm_id)

        ticket.status = "CANCELLED"
        self._commit()
        self.db.refresh(ticket)

        return StatusUpdateResponse(id=ticket.id, status=ticket.status)

    # ─── Internals ───────────────────────────────────────────────────────────

    def _ticket_or_404(self, ticket_id: uuid.UUID) -> Ticket:
        ticket = self.tickets.get(ticket_id)
        if ticket is None:
            raise NotFoundError("Ticket not found.")
        return ticket

    def _require_pm_owns(self, ticket: Ticket, pm_id: uuid.UUID) -> None:
        """
        Ownership runs through the property. `is_active` is intentionally not
        checked: a soft-deleted property keeps its ticket history reachable.
        """
        prop = self.properties.get(ticket.property_id)
        if prop is None or prop.pm_id != pm_id:
            raise ForbiddenError("This ticket does not belong to your properties.")

    def _require_awaiting_approval(self, ticket_id: uuid.UUID, pm_id: uuid.UUID) -> Ticket:
        """
        Guards both approve and reject. Without it a re-approve would resume or
        re-dispatch a ticket that has already moved on.
        """
        ticket = self._ticket_or_404(ticket_id)
        self._require_pm_owns(ticket, pm_id)

        if ticket.status != "PENDING_APPROVAL":
            raise TicketNotAwaitingApprovalError(
                f"Ticket is not awaiting approval (status: {ticket.status})."
            )

        return ticket
