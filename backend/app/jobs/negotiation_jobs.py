"""
app/jobs/negotiation_jobs.py

Follow-ups for a vendor who hasn't replied, and the hand-off to the next vendor.

Registered with Inngest at startup. If Inngest isn't configured this module
still imports cleanly and simply registers nothing — the negotiation works, a
silent vendor just never gets chased.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from app.agentic_AI.runtime import run_async
from app.core.queue import get_client
from app.database import SessionLocal

logger = logging.getLogger(__name__)

INNGEST_FUNCTIONS: list = []


def _build_functions() -> list:
    client = get_client()
    if client is None:
        logger.info("Inngest not configured — no durable jobs registered")
        return []

    import inngest

    @client.create_function(
        fn_id="negotiation-followup",
        trigger=inngest.TriggerEvent(event="negotiation/followup.scheduled"),
    )
    async def negotiation_followup(ctx: inngest.Context) -> None:
        """
        Wait, then chase — or give up and offer the job to someone else.

        `step.sleep_until` hands the clock to Inngest. Nothing is held in this
        process, so the container can redeploy mid-wait and the timer still
        fires. That is the entire reason this is not `asyncio.sleep`.
        """
        data = ctx.event.data
        run_at = datetime.fromisoformat(data["run_at"])
        await ctx.step.sleep_until("wait-for-vendor", run_at)

        await ctx.step.run(
            "chase",
            lambda: _run_followup(
                uuid.UUID(data["vendor_job_id"]),
                expected_round=int(data["expected_round"]),
                armed_at=datetime.fromisoformat(data["armed_at"]),
            ),
        )

    @client.create_function(
        fn_id="negotiation-next-vendor",
        trigger=inngest.TriggerEvent(event="negotiation/next-vendor.requested"),
    )
    async def negotiation_next_vendor(ctx: inngest.Context) -> None:
        """Re-run dispatch for a ticket whose current vendor fell through."""
        ticket_id = uuid.UUID(ctx.event.data["ticket_id"])
        await ctx.step.run("dispatch-next", lambda: _run_next_vendor(ticket_id))

    return [negotiation_followup, negotiation_next_vendor]


def _run_followup(
    job_id: uuid.UUID, *, expected_round: int, armed_at: datetime
) -> None:
    """
    Chase the vendor, or expire the job once the schedule runs out.

    Starts with an atomic claim. If the vendor replied after this timer was
    armed, or Inngest retried the step, or the job already moved on, the claim
    returns 0 rows and this aborts — the reply always wins the race, and it wins
    it in Postgres rather than by luck.
    """
    from app.agentic_AI.tools.negotiation import (
        chat_url_for,
        claim_followup,
        followup_schedule_for,
        mint_chat_token,
        next_followup_at,
        write_message,
    )
    from app.core.channels import channel_for_vendor
    from app.models.ticket import Ticket
    from app.models.vendor import Vendor
    from app.models.vendor_job import VendorJob
    from app.services.negotiation_service import run_timeout

    db = SessionLocal()
    try:
        if not claim_followup(
            db, job_id, expected_round=expected_round, armed_at=armed_at
        ):
            logger.info("Follow-up %s for job %s superseded — no-op", expected_round, job_id)
            return

        job = db.get(VendorJob, job_id)
        if job is None:
            return
        ticket = db.get(Ticket, job.ticket_id)
        vendor = db.get(Vendor, job.vendor_id)
        if ticket is None or vendor is None:
            return

        schedule = followup_schedule_for(ticket.priority)
        if job.followups_sent > len(schedule):
            return

        exhausted = job.followups_sent >= len(schedule)
        if exhausted:
            # Out of chases. Hand it to the graph as a timeout so the job is
            # expired and the next vendor is offered through the normal path.
            logger.info("Follow-ups exhausted for job %s — expiring", job_id)
            run_timeout(job_id)
            return

        body = (
            f"Hi {vendor.name} — just following up on the {ticket.title} job. "
            f"Are you able to take a look and let me know your total?"
        )
        write_message(db, job.id, sender="ai", body=body)
        db.commit()

        token = mint_chat_token(job.id)
        channel = channel_for_vendor(vendor)
        run_async(
            channel.send_message(
                to_email=vendor.email,
                to_phone=vendor.phone,
                vendor_name=vendor.name,
                ticket_title=ticket.title,
                body=body,
                chat_url=chat_url_for(token),
            )
        )

        # Arm only the NEXT one. Arming the whole schedule up front would mean
        # cancelling timers when the vendor replies, and a cancel that fails is
        # a follow-up sent to someone who already answered.
        run_at = next_followup_at(ticket.priority, job.followups_sent)
        if run_at is not None:
            from app.core.queue import emit

            run_async(
                emit(
                    "negotiation/followup.scheduled",
                    {
                        "vendor_job_id": str(job.id),
                        "expected_round": job.followups_sent,
                        "armed_at": datetime.now(tz=timezone.utc).isoformat(),
                        "run_at": run_at.isoformat(),
                    },
                )
            )
    except Exception:
        db.rollback()
        logger.exception("Follow-up failed for job %s", job_id)
    finally:
        db.close()


def _run_next_vendor(ticket_id: uuid.UUID) -> None:
    """Offer the ticket to the next eligible vendor."""
    from app.services.ticket_service import _dispatch_from_db

    try:
        _dispatch_from_db(ticket_id)
    except Exception:
        logger.exception("Next-vendor dispatch failed for ticket %s", ticket_id)


INNGEST_FUNCTIONS = _build_functions()
