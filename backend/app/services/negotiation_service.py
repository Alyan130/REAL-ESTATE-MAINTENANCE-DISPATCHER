"""
app/services/negotiation_service.py

The vendor chat, the PM's decision, and the machinery that wakes a paused graph.

Three things can resume a negotiation — a vendor message, a follow-up timer, and
a PM decision — and all three funnel through `_resume` here. That single entry
point is deliberate: the checkpointer has no per-thread lock, so two concurrent
`ainvoke(Command(resume=...))` calls on one thread corrupt the checkpoint.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Callable, Protocol

import jwt
from sqlalchemy.orm import Session

from app.agentic_AI.runtime import run_async
from app.agentic_AI.tools.negotiation import (
    MAX_COUNTER_ROUNDS,
    build_mandate,
    evaluate_auto_approve,
    load_category_setting,
    load_transcript,
    suggest_counter,
    write_message,
)
from app.agentic_AI.tracing import STAGE_NEGOTIATION, trace_config
from app.core.security import decode_token
from app.database import SessionLocal
from app.exceptions import (
    ChatClosedError,
    ChatLinkExpiredError,
    ChatReadOnlyError,
    CounterLimitReachedError,
    ForbiddenError,
    InvalidTokenError,
    MessageTooFastError,
    NegotiationNotAwaitingDecisionError,
    NegotiationNotFoundError,
    NotFoundError,
)
from app.models.property import Property
from app.models.ticket import Ticket
from app.models.vendor import Vendor
from app.models.vendor_job import TERMINAL_JOB_STATUSES, VendorJob
from app.models.vendor_message import VendorMessage
from app.schemas.negotiation import (
    MessageAcceptedResponse,
    MessageResponse,
    NegotiationDecisionResponse,
    NegotiationResponse,
    VendorChatResponse,
)
from app.services.base import BaseService

logger = logging.getLogger(__name__)

# A job whose status is one of these accepts no further vendor messages, but the
# transcript stays readable — the vendor still needs the history of a job they
# are about to do.
READ_ONLY_JOB_STATUSES = {"APPROVED"}

# Crude flood guard. Two seconds is enough to stop a double-submit and a stuck
# key without ever inconveniencing a human typing a reply.
MIN_MESSAGE_INTERVAL = timedelta(seconds=2)

_LOCK_TTL_SECONDS = 60


class TaskScheduler(Protocol):
    """`BackgroundTasks.add_task`, narrowed so this module imports no FastAPI."""

    def __call__(self, func: Callable[..., object], /, *args: object) -> object: ...


# ─── Resuming a paused graph ─────────────────────────────────────────────────


def _redis_client():
    """
    A Redis client for the resume lock.

    This is the only thing Redis still does — the checkpointer moved to Postgres.
    A lock is plain `SET NX EX`, so any Redis works, with no modules required.

    `rediss://` turns on TLS, and redis-py then verifies against whatever CA
    store Python was built with; on Windows that store is often empty and a
    healthy endpoint fails with CERTIFICATE_VERIFY_FAILED. Pointing at certifi's
    bundle fixes that without weakening verification.
    """
    import redis

    from app.config import settings

    kwargs = {}
    if settings.REDIS_URL.startswith("rediss://"):
        import certifi

        kwargs["ssl_ca_certs"] = certifi.where()
    return redis.from_url(settings.REDIS_URL, **kwargs)


def _acquire_lock(thread_id: str) -> bool:
    """
    One resume at a time per thread.

    The saver has no per-thread lock of its own, so without this a vendor
    message and a follow-up timer arriving together would both call resume and
    leave the checkpoint inconsistent. Failing to acquire is not an error — the
    database claim has already decided who wins, so the loser just drops.
    """
    try:
        return bool(
            _redis_client().set(
                f"lock:graph:{thread_id}", "1", nx=True, ex=_LOCK_TTL_SECONDS
            )
        )
    except Exception:
        # A Redis failure must not block the negotiation. The kind-assertions
        # inside each interrupt node are the remaining line of defence.
        logger.exception("Could not acquire graph lock for %s — proceeding", thread_id)
        return True


def _release_lock(thread_id: str) -> None:
    try:
        _redis_client().delete(f"lock:graph:{thread_id}")
    except Exception:
        logger.debug("Could not release graph lock for %s", thread_id)


async def _resume_negotiation(job_id: uuid.UUID, resume_value: dict) -> bool:
    """
    Resume the paused negotiation for this job.

    Returns False when there is no live interrupt to resume — the checkpoint
    expired, or the graph already moved on — so the caller can fall back to a
    rebuild.
    """
    from langgraph.types import Command

    from app.agentic_AI.agents.orchestration_agent import (
        get_parent_graph,
        get_post_approval_graph,
    )
    from app.agentic_AI.checkpointer import get_checkpointer

    db = SessionLocal()
    try:
        job = db.get(VendorJob, job_id)
        thread_id = job.negotiation_thread_id if job else None
    finally:
        db.close()

    if not thread_id:
        logger.info("Job %s has no negotiation thread — cannot resume", job_id)
        return False

    if not _acquire_lock(thread_id):
        logger.info("Another resume holds the lock on %s — dropping", thread_id)
        return False

    try:
        config = trace_config(
            thread_id,
            stage=STAGE_NEGOTIATION,
            run_name=f"negotiation-resume:{job_id}",
            vendor_job_id=str(job_id),
            resume_kind=resume_value.get("kind") if isinstance(resume_value, dict) else None,
        )
        async with get_checkpointer() as checkpointer:
            # The thread id records which graph owns it: the parent graph runs
            # the whole intake→dispatch→negotiate pipeline on "ticket-…", while
            # the post-approval fallback uses "dispatch-…".
            graph = (
                get_parent_graph(checkpointer)
                if thread_id.startswith("ticket-")
                else get_post_approval_graph(checkpointer)
            )
            snapshot = await graph.aget_state(config)
            if not snapshot or not snapshot.next:
                return False
            await graph.ainvoke(Command(resume=resume_value), config=config)
            return True
    finally:
        _release_lock(thread_id)


def _negotiate_from_db(job_id: uuid.UUID, resume_value: dict | None = None) -> None:
    """
    Rebuild a negotiation whose checkpoint is gone.

    With the Postgres checkpointer there is no TTL, so this is now a genuine
    recovery path rather than the routine one it was under Redis's 3-day expiry.
    It still has to work: a thread can be lost to a wiped database or a manual
    intervention. `open_negotiation`'s `negotiation_opened_at` guard is what
    makes re-entry safe — the offer email is never sent twice.
    """
    from app.agentic_AI.agents.negotiation_agent import get_negotiation_graph
    from app.agentic_AI.checkpointer import get_checkpointer
    from app.agentic_AI.ticket_state import TicketState

    db: Session = SessionLocal()
    try:
        job = db.get(VendorJob, job_id)
        if job is None:
            logger.error("Job %s not found for negotiation rebuild", job_id)
            return

        ticket = db.get(Ticket, job.ticket_id)
        prop = db.get(Property, ticket.property_id) if ticket else None
        if ticket is None or prop is None:
            logger.error("Ticket or property missing for job %s", job_id)
            return

        thread_id = f"negotiation-{job.id}-{int(datetime.now(tz=timezone.utc).timestamp())}"
        job.negotiation_thread_id = thread_id
        db.commit()

        state = TicketState(
            ticket_id=str(ticket.id),
            tenant_id=str(ticket.tenant_id),
            property_id=str(ticket.property_id),
            pm_id=str(prop.pm_id),
            category=ticket.category,
            priority=ticket.priority,
            ai_summary=ticket.ai_summary,
            pm_approved=True,
            active_vendor_job_id=str(job.id),
            negotiation_thread_id=thread_id,
            counter_rounds=job.counter_rounds,
            quoted_price=float(job.quote_amount) if job.quote_amount else None,
            quoted_availability=job.availability_text,
        )
        config = trace_config(
            thread_id,
            stage=STAGE_NEGOTIATION,
            run_name=f"negotiation-rebuild:{job.id}",
            ticket_id=str(ticket.id),
            pm_id=str(prop.pm_id),
            vendor_job_id=str(job.id),
            priority=ticket.priority,
            counter_rounds=job.counter_rounds,
            # Expected, not exceptional — the checkpoint TTL is shorter than a
            # P4 window. Tagged so it can be told apart from a live resume.
            rebuilt_from_db=True,
        )

        async def _run() -> None:
            async with get_checkpointer() as checkpointer:
                graph = get_negotiation_graph(checkpointer)
                # Runs to the first interrupt, which re-enters the wait.
                await graph.ainvoke(state.model_dump(), config=config)
                if resume_value is not None:
                    from langgraph.types import Command

                    await graph.ainvoke(Command(resume=resume_value), config=config)

        run_async(_run())
        logger.info("Rebuilt negotiation for job %s on %s", job_id, thread_id)
    except Exception:
        logger.exception("Negotiation rebuild failed for job %s", job_id)
    finally:
        db.close()


def _resume(job_id: uuid.UUID, resume_value: dict) -> None:
    """Try a live resume; rebuild from the database if the checkpoint is gone."""
    try:
        if run_async(_resume_negotiation(job_id, resume_value)):
            return
        logger.warning("No live checkpoint for job %s — rebuilding", job_id)
        _negotiate_from_db(job_id, resume_value)
    except Exception:
        logger.exception("Resume failed for job %s", job_id)


# ─── Background entry points ─────────────────────────────────────────────────


def run_vendor_reply(job_id: uuid.UUID, message_id: uuid.UUID, body: str) -> None:
    """
    Push a vendor's message into the graph.

    Uses BackgroundTasks rather than Inngest: a vendor waiting on a reply should
    not eat a queue round trip. The trade-off is no automatic retry on a
    transient OpenAI failure, which is why a failure writes a visible `system`
    message instead of disappearing.
    """
    try:
        _resume(job_id, {"kind": "vendor_message", "message_id": str(message_id), "body": body})
    except Exception:
        logger.exception("run_vendor_reply failed for job %s", job_id)
        _write_system_message(
            job_id,
            "Thanks — we've got your message and will come back to you shortly.",
        )


def run_pm_decision(
    job_id: uuid.UUID, action: str, counter_price: float | None = None
) -> None:
    _resume(
        job_id,
        {"kind": "pm_decision", "action": action, "counter_price": counter_price},
    )


def run_timeout(job_id: uuid.UUID) -> None:
    _resume(job_id, {"kind": "timeout"})


def _write_system_message(job_id: uuid.UUID, body: str) -> None:
    db = SessionLocal()
    try:
        write_message(db, job_id, sender="system", body=body)
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("Could not write system message for job %s", job_id)
    finally:
        db.close()


# ─── Service ─────────────────────────────────────────────────────────────────


class NegotiationService(BaseService):
    def __init__(self, db: Session) -> None:
        super().__init__(db)

    # ─── Vendor-facing ───────────────────────────────────────────────────────

    def get_chat(self, token: str) -> VendorChatResponse:
        job, vendor, ticket = self._authorise_chat(token)
        mandate = build_mandate(self.db, job)
        messages = load_transcript(self.db, job.id)

        return VendorChatResponse(
            vendor_job_id=job.id,
            vendor_name=vendor.name,
            ticket_title=mandate.ticket_title,
            ticket_summary=mandate.ticket_summary,
            category_label=mandate.category_label,
            priority_label=mandate.priority_label,
            property_label=mandate.property_label,
            access_note=mandate.access_note,
            media_urls=list(ticket.media_urls or []),
            status=job.status,
            can_reply=job.status not in READ_ONLY_JOB_STATUSES,
            messages=[MessageResponse.model_validate(m) for m in messages],
        )

    def post_message(
        self, token: str, body: str, schedule: TaskScheduler
    ) -> MessageAcceptedResponse:
        """
        Store the vendor's message, then wake the graph in the background.

        The write and `last_vendor_message_at` land in the same transaction. That
        timestamp is what a follow-up timer compares itself against, so if it
        were written separately a reply could be counted as "no reply" by a timer
        that fired in between.
        """
        job, _vendor, _ticket = self._authorise_chat(token)

        if job.status in READ_ONLY_JOB_STATUSES:
            raise ChatReadOnlyError()

        self._require_not_flooding(job.id)

        message = write_message(self.db, job.id, sender="vendor", body=body)
        job.last_vendor_message_at = datetime.now(tz=timezone.utc)
        self._commit()
        self.db.refresh(message)

        schedule(run_vendor_reply, job.id, message.id, body)

        return MessageAcceptedResponse(id=message.id, created_at=message.created_at)

    # ─── PM-facing ───────────────────────────────────────────────────────────

    def get_for_ticket(self, ticket_id: uuid.UUID, pm_id: uuid.UUID) -> NegotiationResponse:
        ticket, prop = self._pm_ticket(ticket_id, pm_id)

        job = (
            self.db.query(VendorJob)
            .filter(
                VendorJob.ticket_id == ticket_id,
                VendorJob.status.notin_(TERMINAL_JOB_STATUSES),
            )
            .order_by(VendorJob.created_at.desc())
            .first()
        )
        if job is None:
            raise NegotiationNotFoundError()

        vendor = self.db.get(Vendor, job.vendor_id)
        setting = load_category_setting(self.db, pm_id, ticket.category)
        mandate = build_mandate(self.db, job)

        counter = None
        if job.quote_amount is not None:
            counter = suggest_counter(
                quoted=job.quote_amount,
                anchor=mandate.anchor_price,
                max_price=setting.max_price if setting else None,
            )

        messages = load_transcript(self.db, job.id)
        latest = next(
            (m.extracted for m in reversed(messages) if m.extracted), None
        ) or {}

        # Why the PM is being asked, in their terms — "$650.00 is over the
        # $400.00 ceiling", not the model's note about whether the quote was
        # firm. Recomputed from the same function that made the call rather than
        # stored, so the card can never disagree with the decision itself.
        #
        # The model's own reasoning is the fallback: it is the right answer when
        # the price cleared the ceiling and the *hedging* is what stopped it.
        decision_reason = latest.get("reasoning")
        if job.quote_amount is not None:
            verdict = evaluate_auto_approve(
                price=job.quote_amount,
                ai_recommendation=latest.get("recommendation"),
                max_price=setting.max_price if setting else None,
            )
            if not verdict.approved:
                decision_reason = verdict.reason

        return NegotiationResponse(
            vendor_job_id=job.id,
            vendor_name=vendor.name if vendor else "Vendor",
            vendor_rating=float(vendor.rating) if vendor and vendor.rating else None,
            status=job.status,
            quoted_price=job.quote_amount,
            availability=job.availability_text,
            target_price=setting.target_price if setting else None,
            max_price=setting.max_price if setting else None,
            suggested_counter=counter,
            decision_reason=decision_reason,
            counter_rounds_used=job.counter_rounds,
            counter_allowed=job.counter_rounds < MAX_COUNTER_ROUNDS,
            awaiting_decision=job.status == "QUOTED",
            messages=[MessageResponse.model_validate(m) for m in messages],
        )

    def decide(
        self,
        ticket_id: uuid.UUID,
        pm_id: uuid.UUID,
        action: str,
        counter_price: Decimal | None,
        schedule: TaskScheduler,
    ) -> NegotiationDecisionResponse:
        """
        Record the PM's decision and hand off to the graph.

        Everything is validated synchronously so a double-click gets a 409 rather
        than scheduling two resumes. The counter cap is checked here as well as
        in the router and the column — a bug in this one spends the PM's money.
        """
        self._pm_ticket(ticket_id, pm_id)

        job = (
            self.db.query(VendorJob)
            .filter(
                VendorJob.ticket_id == ticket_id,
                VendorJob.status.notin_(TERMINAL_JOB_STATUSES),
            )
            .order_by(VendorJob.created_at.desc())
            .first()
        )
        if job is None:
            raise NegotiationNotFoundError()

        if action not in {"accept", "counter", "next_vendor"}:
            raise InvalidTokenError("Unknown decision.")

        if job.status != "QUOTED":
            raise NegotiationNotAwaitingDecisionError()

        if action == "counter":
            if job.counter_rounds >= MAX_COUNTER_ROUNDS:
                raise CounterLimitReachedError()
            if counter_price is None or counter_price <= 0:
                raise InvalidTokenError("A counter needs a price.")

        # Move the job off QUOTED so a second submission 409s on the guard above.
        job.status = "PENDING" if action == "counter" else job.status
        if action == "next_vendor":
            job.status = "SUPERSEDED"
        self._commit()

        schedule(
            run_pm_decision,
            job.id,
            action,
            float(counter_price) if counter_price is not None else None,
        )

        return NegotiationDecisionResponse(vendor_job_id=job.id, action=action)

    # ─── Internals ───────────────────────────────────────────────────────────

    def _authorise_chat(self, token: str) -> tuple[VendorJob, Vendor, Ticket]:
        """
        Turn a chat token into a job, or refuse.

        Structured 1:1 against `AuthService._decode_invite`, with one addition
        that matters: the `type` check. A login or invite JWT presented here must
        be rejected outright rather than being allowed to decode into something
        that happens not to resolve.
        """
        try:
            payload = decode_token(token)
        except jwt.ExpiredSignatureError:
            raise ChatLinkExpiredError()
        except jwt.PyJWTError:
            raise InvalidTokenError("This link isn't valid.")

        if payload.get("type") != "job" or payload.get("role") != "vendor":
            raise InvalidTokenError("This link isn't valid.")

        try:
            job_id = uuid.UUID(str(payload.get("sub")))
        except (TypeError, ValueError):
            raise InvalidTokenError("This link isn't valid.")

        job = self.db.get(VendorJob, job_id)
        if job is None:
            raise NotFoundError("This job no longer exists.")

        # The job's status is the revocation mechanism — nothing is stored, so
        # this check is the whole of "is this link still live?".
        if job.status in TERMINAL_JOB_STATUSES:
            raise ChatClosedError()

        vendor = self.db.get(Vendor, job.vendor_id)
        if vendor is None or not vendor.is_active:
            raise ChatClosedError()

        ticket = self.db.get(Ticket, job.ticket_id)
        if ticket is None:
            raise NotFoundError("This job no longer exists.")

        return job, vendor, ticket

    def _require_not_flooding(self, job_id: uuid.UUID) -> None:
        cutoff = datetime.now(tz=timezone.utc) - MIN_MESSAGE_INTERVAL
        recent = (
            self.db.query(VendorMessage)
            .filter(
                VendorMessage.vendor_job_id == job_id,
                VendorMessage.sender == "vendor",
                VendorMessage.created_at > cutoff,
            )
            .first()
        )
        if recent is not None:
            raise MessageTooFastError()

    def _pm_ticket(self, ticket_id: uuid.UUID, pm_id: uuid.UUID) -> tuple[Ticket, Property]:
        ticket = self.db.get(Ticket, ticket_id)
        if ticket is None:
            raise NotFoundError("Ticket not found.")
        prop = self.db.get(Property, ticket.property_id)
        if prop is None or prop.pm_id != pm_id:
            raise ForbiddenError("This ticket does not belong to your properties.")
        return ticket, prop
