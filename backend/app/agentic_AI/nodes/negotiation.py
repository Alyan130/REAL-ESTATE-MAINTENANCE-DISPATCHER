"""
backend/agentic_AI/nodes/negotiation.py

Negotiation agent graph nodes. An AI chats with the selected vendor inside the
platform, extracts a price and availability, and either auto-approves the quote
against the PM's ceiling or hands the PM a decision card.

Node convention (mirrors nodes/dispatch.py): each node is
`async def node(state) -> dict`, opens its own SessionLocal, wraps its body in
try/except → logger.exception + `{"error": ...}`, closes in finally, and returns
only the state keys it changed.

**The interrupt rule that governs this whole module:** on resume, an interrupted
node re-runs from its first line. So `interrupt()` must be statement one, and
every side effect belongs in the node *before* it — `open_negotiation` before
interrupt #1, `notify_pm_quote` before interrupt #2. This is the same
`notify_pm_node → human_approval_node` shape the orchestration graph already
uses, and breaking it means re-sending emails on every vendor message.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict

from langchain_core.messages import HumanMessage
from langgraph.types import interrupt

from app.agentic_AI import prompts
from app.agentic_AI.llm import get_structured_model
from app.agentic_AI.output_schemas import (
    VENDOR_INTENTS,
    VENDOR_RECOMMENDATIONS,
    VendorReplyExtraction,
)
from app.agentic_AI.ticket_state import TicketState
from app.agentic_AI.tools.negotiation import (
    MAX_CHAT_TURNS,
    MAX_COUNTER_ROUNDS,
    build_mandate,
    chat_url_for,
    evaluate_auto_approve,
    load_category_setting,
    load_transcript,
    mark_approved,
    mark_closed,
    mark_quoted,
    mint_chat_token,
    next_followup_at,
    price_appears_in_text,
    render_transcript,
    select_context_messages,
    write_message,
)
from app.core.channels import channel_for_vendor
from app.core.email import send_job_confirmed_email
from app.database import SessionLocal
from app.models.notification import Notification
from app.models.property import Property
from app.models.ticket import Ticket
from app.models.vendor import Vendor
from app.models.vendor_job import VendorJob

logger = logging.getLogger(__name__)


# ─── Helpers ─────────────────────────────────────────────────────────────────


async def _arm_followup(job: VendorJob, priority: str | None) -> None:
    """
    Schedule the next chase, if the schedule isn't exhausted.

    Fire-and-forget by design: a timer that fails to arm must never roll back
    the negotiation turn that armed it. Worst case the vendor is not chased and
    the PM sees a stalled ticket — bad, but far better than a lost message.
    """
    run_at = next_followup_at(priority, job.followups_sent)
    if run_at is None:
        return

    from app.core.queue import emit

    await emit(
        "negotiation/followup.scheduled",
        {
            "vendor_job_id": str(job.id),
            "expected_round": job.followups_sent,
            "armed_at": datetime.now(tz=timezone.utc).isoformat(),
            "run_at": run_at.isoformat(),
        },
    )


def _sanitize_reply(draft: str, authorised: set[Decimal]) -> str:
    """
    Refuse to send a money figure nobody approved.

    The model has been told not to invent numbers, but "told not to" is not a
    guarantee, and the cost of one leaked figure is a price the PM never agreed
    to — in writing, to a contractor, from an account that speaks for them.

    Authorised means: a counter the PM explicitly approved, or a figure the
    vendor themselves just named (echoing their own number back is normal and
    necessary). Anything else and we send a safe canned line instead.
    """
    from app.agentic_AI.tools.negotiation import _money_tokens

    found = _money_tokens(draft)
    unauthorised = {
        value
        for value in found
        # Below $20 is almost always a time ("2 hours"), a date, or a quantity,
        # not a price. Treating those as money would reject nearly every reply.
        if value >= 20 and not any(value == ok for ok in authorised)
    }
    if unauthorised:
        logger.warning(
            "Blocked unauthorised figure(s) %s in drafted reply", sorted(unauthorised)
        )
        return prompts.NEGOTIATION_FALLBACK_REPLY
    return draft


def _validate_extraction(
    extraction: VendorReplyExtraction, vendor_text: str
) -> VendorReplyExtraction:
    """
    Fold the model's answer back onto what the vendor actually said.

    Structured output guarantees the shape of the reply, never its truth. A
    model reading "sounds like about two hundred" can emit `price: 200.0` with
    total confidence, and that becomes a $200 job nobody quoted. If the figure
    is not in the vendor's own words, it is dropped and the turn is sent to the
    PM instead.
    """
    price = extraction.price
    recommendation = extraction.recommendation
    intent = extraction.intent

    if price is not None and not price_appears_in_text(price, vendor_text):
        logger.warning(
            "Extraction claimed price %s not present in vendor text — dropping", price
        )
        price = None
        intent = "unclear"
        recommendation = "send_to_pm"

    if intent not in VENDOR_INTENTS:
        intent = "unclear"
    if recommendation not in VENDOR_RECOMMENDATIONS:
        recommendation = "send_to_pm"

    return extraction.model_copy(
        update={
            "price": price,
            "intent": intent,
            "recommendation": recommendation,
        }
    )


# ─── Nodes ───────────────────────────────────────────────────────────────────


async def open_negotiation_node(state: TicketState) -> Dict[str, Any]:
    """
    Mint the chat token, send the offer, write the AI's opener, arm the timer.

    Idempotent on `negotiation_opened_at`: the fallback path rebuilds this graph
    from the database when a checkpoint has expired, and re-entering here must
    not mail the vendor a second offer for the same job.

    Every field it returns is a reset, not an update — vendor #2 runs on the
    same TicketState as vendor #1, so stale quote data has to be cleared here or
    it silently carries over.
    """
    if not state.active_vendor_job_id:
        logger.warning("open_negotiation: no active job for ticket %s", state.ticket_id)
        return {"error": "no vendor job to negotiate"}

    db = SessionLocal()
    try:
        job = db.get(VendorJob, uuid.UUID(state.active_vendor_job_id))
        if job is None:
            return {"error": "vendor job not found"}

        reset: Dict[str, Any] = {
            "quoted_price": None,
            "quoted_availability": None,
            "vendor_intent": None,
            "is_firm_total": None,
            "ai_recommendation": None,
            "ai_reasoning": None,
            "counter_rounds": job.counter_rounds,
            "chat_turns": 0,
            "auto_approved": None,
            "decision_reason": None,
            "pm_negotiation_action": None,
            "pm_counter_price": None,
            "close_reason": None,
        }

        if job.negotiation_opened_at is not None:
            # Already opened — this is a rebuild, not a fresh dispatch.
            logger.info("Negotiation already open for job %s — resuming", job.id)
            return {**reset, "chat_token": mint_chat_token(job.id)}

        ticket = db.get(Ticket, job.ticket_id)
        vendor = db.get(Vendor, job.vendor_id)
        if ticket is None or vendor is None:
            return {"error": "ticket or vendor missing"}

        mandate = build_mandate(db, job)
        token = mint_chat_token(job.id)
        chat_url = chat_url_for(token)

        opener = prompts.NEGOTIATION_OPENER.format(
            vendor_name=vendor.name,
            category_label=mandate.category_label,
            property_label=mandate.property_label,
            ticket_title=mandate.ticket_title,
            ticket_summary=mandate.ticket_summary,
        )

        write_message(db, job.id, sender="ai", body=opener)
        job.negotiation_opened_at = datetime.now(tz=timezone.utc)
        # Mirror the thread onto the row so a later resume can find this
        # negotiation without reconstructing a naming convention.
        if state.negotiation_thread_id:
            job.negotiation_thread_id = state.negotiation_thread_id
        db.commit()

        channel = channel_for_vendor(vendor)
        await channel.send_job_offer(
            to_email=vendor.email,
            to_phone=vendor.phone,
            vendor_name=vendor.name,
            ticket_title=mandate.ticket_title,
            ticket_summary=mandate.ticket_summary,
            chat_url=chat_url,
        )

        await _arm_followup(job, ticket.priority)

        return {
            **reset,
            "chat_token": token,
            "negotiation_messages": [
                {"vendor_job_id": str(job.id), "sender": "ai", "body": opener}
            ],
            "current_status": "NEGOTIATING",
        }
    except Exception as e:
        db.rollback()
        logger.exception("open_negotiation error for %s: %s", state.ticket_id, e)
        return {"error": str(e)}
    finally:
        db.close()


async def await_vendor_reply_node(state: TicketState) -> Dict[str, Any]:
    """
    Pause until the vendor sends a message or a follow-up timer gives up.

    interrupt() is the first statement, and nothing side-effecting may precede
    it — the node re-runs top-to-bottom every time the graph resumes.
    """
    signal = interrupt(
        {
            "kind": "vendor_message",
            "vendor_job_id": state.active_vendor_job_id,
            "ticket_id": state.ticket_id,
            "turn": state.chat_turns,
        }
    )

    # Last line of defence against a misrouted resume: if the payload is not the
    # kind this node is waiting for, pause again rather than acting on it.
    if not isinstance(signal, dict) or signal.get("kind") not in {
        "vendor_message",
        "timeout",
    }:
        logger.error("await_vendor_reply got unexpected resume payload: %r", signal)
        return {}

    if signal.get("kind") == "timeout":
        return {"close_reason": "EXPIRED"}

    return {
        "chat_turns": state.chat_turns + 1,
        "negotiation_messages": [
            {
                "vendor_job_id": state.active_vendor_job_id,
                "sender": "vendor",
                "body": signal.get("body", ""),
            }
        ],
    }


async def interpret_reply_node(state: TicketState) -> Dict[str, Any]:
    """
    One LLM call: draft the response and extract what the vendor's message meant.

    The vendor's text is untrusted input. It reaches the model, but the model's
    output only ever lands in typed fields — the free text never becomes an
    instruction, and the ceiling it might try to talk its way past was never in
    this context to begin with.
    """
    if state.close_reason:  # timed out — nothing to interpret
        return {}

    db = SessionLocal()
    try:
        job = db.get(VendorJob, uuid.UUID(state.active_vendor_job_id))
        if job is None:
            return {"error": "vendor job not found"}

        messages = load_transcript(db, job.id)
        vendor_messages = [m for m in messages if m.sender == "vendor"]
        if not vendor_messages:
            logger.warning("interpret_reply: no vendor message on job %s", job.id)
            return {}
        latest = vendor_messages[-1]

        authorised_counter = (
            Decimal(str(state.pm_counter_price))
            if state.pm_counter_price is not None
            else None
        )
        mandate = build_mandate(db, job, authorised_counter=authorised_counter)
        transcript = render_transcript(select_context_messages(messages))

        structured_llm = get_structured_model(VendorReplyExtraction)
        raw: VendorReplyExtraction = await structured_llm.ainvoke(
            [HumanMessage(content=prompts.build_negotiation_prompt(mandate, transcript))]
        )

        extraction = _validate_extraction(raw, latest.body)

        # Record the judgement against the message it was made about, so a later
        # turn can pin this one into context if it carried a price or a caveat.
        latest.extracted = {
            "price": extraction.price,
            "availability": extraction.availability,
            "intent": extraction.intent,
            "is_firm_total": extraction.is_firm_total,
            "recommendation": extraction.recommendation,
            "reasoning": extraction.reasoning,
        }
        db.commit()

        return {
            "quoted_price": extraction.price,
            "quoted_availability": extraction.availability,
            "vendor_intent": extraction.intent,
            "is_firm_total": extraction.is_firm_total,
            "ai_recommendation": extraction.recommendation,
            "ai_reasoning": extraction.reasoning,
            "pending_reply": extraction.reply,
        }
    except Exception as e:
        db.rollback()
        logger.exception("interpret_reply error for %s: %s", state.ticket_id, e)
        return {"error": str(e)}
    finally:
        db.close()


async def post_ai_reply_node(state: TicketState) -> Dict[str, Any]:
    """Send the drafted reply and go back to waiting."""
    db = SessionLocal()
    try:
        job = db.get(VendorJob, uuid.UUID(state.active_vendor_job_id))
        if job is None:
            return {"error": "vendor job not found"}

        vendor = db.get(Vendor, job.vendor_id)
        ticket = db.get(Ticket, job.ticket_id)
        if vendor is None or ticket is None:
            return {"error": "ticket or vendor missing"}

        authorised: set[Decimal] = set()
        if state.pm_counter_price is not None:
            authorised.add(Decimal(str(state.pm_counter_price)))
        if state.quoted_price is not None:
            authorised.add(Decimal(str(state.quoted_price)))

        body = _sanitize_reply(
            state.pending_reply or prompts.NEGOTIATION_FALLBACK_REPLY, authorised
        )

        write_message(db, job.id, sender="ai", body=body)
        db.commit()

        token = state.chat_token or mint_chat_token(job.id)
        channel = channel_for_vendor(vendor)
        await channel.send_message(
            to_email=vendor.email,
            to_phone=vendor.phone,
            vendor_name=vendor.name,
            ticket_title=ticket.title,
            body=body,
            chat_url=chat_url_for(token),
        )

        await _arm_followup(job, ticket.priority)

        return {
            "pending_reply": None,
            "negotiation_messages": [
                {"vendor_job_id": str(job.id), "sender": "ai", "body": body}
            ],
        }
    except Exception as e:
        db.rollback()
        logger.exception("post_ai_reply error for %s: %s", state.ticket_id, e)
        return {"error": str(e)}
    finally:
        db.close()


async def evaluate_quote_node(state: TicketState) -> Dict[str, Any]:
    """
    Record the quote and apply the one decision that stays in code.

    The model already judged whether the quote is firm and sensible. This adds
    the ceiling — the single number it was never shown.
    """
    db = SessionLocal()
    try:
        job = db.get(VendorJob, uuid.UUID(state.active_vendor_job_id))
        if job is None:
            return {"error": "vendor job not found"}

        ticket = db.get(Ticket, job.ticket_id)
        prop = db.get(Property, ticket.property_id) if ticket else None
        if ticket is None or prop is None:
            return {"error": "ticket or property missing"}

        setting = load_category_setting(db, prop.pm_id, ticket.category)
        max_price = setting.max_price if setting else None

        mark_quoted(
            db,
            job,
            price=state.quoted_price,
            availability=state.quoted_availability,
        )
        db.commit()

        decision = evaluate_auto_approve(
            price=state.quoted_price,
            ai_recommendation=state.ai_recommendation,
            max_price=max_price,
        )

        return {
            "auto_approved": decision.approved,
            "decision_reason": decision.reason,
            "final_price": state.quoted_price,
        }
    except Exception as e:
        db.rollback()
        logger.exception("evaluate_quote error for %s: %s", state.ticket_id, e)
        return {"error": str(e)}
    finally:
        db.close()


async def notify_pm_quote_node(state: TicketState) -> Dict[str, Any]:
    """
    Put the quote in front of the PM. Runs *before* the interrupt, so it fires
    exactly once no matter how many times the pause is resumed.
    """
    db = SessionLocal()
    try:
        job = db.get(VendorJob, uuid.UUID(state.active_vendor_job_id))
        if job is None:
            return {"error": "vendor job not found"}

        vendor = db.get(Vendor, job.vendor_id)
        ticket = db.get(Ticket, job.ticket_id)
        if ticket is None:
            return {"error": "ticket not found"}

        db.add(
            Notification(
                id=uuid.uuid4(),
                user_id=uuid.UUID(state.pm_id),
                type="QUOTE_NEEDS_DECISION",
                title="A quote needs your decision",
                message=(
                    f"{vendor.name if vendor else 'A vendor'} quoted "
                    f"${state.quoted_price:,.2f} for {ticket.title}. "
                    f"{state.decision_reason or ''}"
                ).strip(),
                is_read=False,
            )
        )
        ticket.status = "QUOTED"
        ticket.updated_at = datetime.utcnow()
        db.commit()

        return {"current_status": "QUOTED"}
    except Exception as e:
        db.rollback()
        logger.exception("notify_pm_quote error for %s: %s", state.ticket_id, e)
        return {"error": str(e)}
    finally:
        db.close()


async def await_pm_decision_node(state: TicketState) -> Dict[str, Any]:
    """Pause until the PM accepts, counters, or moves to the next vendor."""
    decision = interrupt(
        {
            "kind": "pm_decision",
            "vendor_job_id": state.active_vendor_job_id,
            "ticket_id": state.ticket_id,
            "quoted_price": state.quoted_price,
            "availability": state.quoted_availability,
            "reason": state.decision_reason,
            "counter_rounds_used": state.counter_rounds,
            "counter_allowed": state.counter_rounds < MAX_COUNTER_ROUNDS,
        }
    )

    if not isinstance(decision, dict) or decision.get("kind") != "pm_decision":
        logger.error("await_pm_decision got unexpected resume payload: %r", decision)
        return {}

    action = decision.get("action")
    if action not in {"accept", "counter", "next_vendor"}:
        logger.error("await_pm_decision got unknown action %r", action)
        return {}

    return {
        "pm_negotiation_action": action,
        "pm_counter_price": decision.get("counter_price"),
    }


async def send_counter_node(state: TicketState) -> Dict[str, Any]:
    """
    Put the PM's authorised counter to the vendor.

    This is the only path on which the AI states a price, and the figure comes
    from the PM — never from the model. `counter_rounds` is incremented in
    Postgres so the cap survives a checkpoint loss.
    """
    db = SessionLocal()
    try:
        job = db.get(VendorJob, uuid.UUID(state.active_vendor_job_id))
        if job is None:
            return {"error": "vendor job not found"}

        vendor = db.get(Vendor, job.vendor_id)
        ticket = db.get(Ticket, job.ticket_id)
        if vendor is None or ticket is None:
            return {"error": "ticket or vendor missing"}

        counter = Decimal(str(state.pm_counter_price))
        body = (
            f"Thanks for the quote. The property manager has come back and can "
            f"approve ${counter:,.2f} for this job — would that work for you?"
        )

        write_message(db, job.id, sender="ai", body=body)
        job.counter_rounds += 1
        job.status = "PENDING"  # back to negotiating
        db.commit()

        token = state.chat_token or mint_chat_token(job.id)
        channel = channel_for_vendor(vendor)
        await channel.send_message(
            to_email=vendor.email,
            to_phone=vendor.phone,
            vendor_name=vendor.name,
            ticket_title=ticket.title,
            body=body,
            chat_url=chat_url_for(token),
        )

        await _arm_followup(job, ticket.priority)

        return {
            "counter_rounds": job.counter_rounds,
            "counter_offered": True,
            "pm_negotiation_action": None,
            "negotiation_messages": [
                {"vendor_job_id": str(job.id), "sender": "ai", "body": body}
            ],
        }
    except Exception as e:
        db.rollback()
        logger.exception("send_counter error for %s: %s", state.ticket_id, e)
        return {"error": str(e)}
    finally:
        db.close()


async def confirm_job_node(state: TicketState) -> Dict[str, Any]:
    """Job agreed — approve it and send the vendor the details, address included."""
    db = SessionLocal()
    try:
        job = db.get(VendorJob, uuid.UUID(state.active_vendor_job_id))
        if job is None:
            return {"error": "vendor job not found"}

        vendor = db.get(Vendor, job.vendor_id)
        ticket = db.get(Ticket, job.ticket_id)
        prop = db.get(Property, ticket.property_id) if ticket else None
        if ticket is None:
            return {"error": "ticket not found"}

        # An accepted counter is the agreed price, even though the vendor's own
        # last quote may have been higher.
        agreed = state.pm_counter_price or state.quoted_price
        if agreed is not None:
            job.quote_amount = Decimal(str(agreed))
            job.quoted_at = job.quoted_at or datetime.now(tz=timezone.utc)

        mark_approved(db, job)
        write_message(
            db,
            job.id,
            sender="system",
            body=f"Job confirmed at ${Decimal(str(agreed)):,.2f}." if agreed else "Job confirmed.",
        )
        ticket.status = "APPROVED"
        ticket.updated_at = datetime.utcnow()
        db.commit()

        if vendor and vendor.email:
            import asyncio

            await asyncio.to_thread(
                send_job_confirmed_email,
                to_email=vendor.email,
                vendor_name=vendor.name,
                ticket_title=ticket.title,
                price=f"${Decimal(str(agreed)):,.2f}" if agreed else "as discussed",
                availability=state.quoted_availability or "to be arranged",
                property_address=(prop.address if prop else "") or (prop.name if prop else ""),
            )

        return {
            "job_confirmed": True,
            "final_price": float(agreed) if agreed is not None else None,
            "current_status": "APPROVED",
        }
    except Exception as e:
        db.rollback()
        logger.exception("confirm_job error for %s: %s", state.ticket_id, e)
        return {"error": str(e)}
    finally:
        db.close()


async def close_negotiation_node(state: TicketState) -> Dict[str, Any]:
    """
    This vendor is out. Close the job terminally (which kills its chat link) and
    ask for the next vendor.

    The ticket goes back to DISPATCHING rather than NEEDS_ATTENTION: there may
    well be another vendor, and `find_best_vendor` already excludes everyone
    already contacted for this ticket.
    """
    db = SessionLocal()
    try:
        job = db.get(VendorJob, uuid.UUID(state.active_vendor_job_id))
        if job is None:
            return {"error": "vendor job not found"}

        reason = state.close_reason or (
            "DECLINED" if state.vendor_intent == "decline" else "SUPERSEDED"
        )
        mark_closed(db, job, reason)
        if state.ai_reasoning:
            job.declined_reason = state.ai_reasoning

        ticket = db.get(Ticket, job.ticket_id)
        if ticket:
            ticket.status = "DISPATCHING"
            ticket.updated_at = datetime.utcnow()
        db.commit()

        from app.core.queue import emit

        await emit(
            "negotiation/next-vendor.requested",
            {"ticket_id": state.ticket_id, "closed_job_id": str(job.id)},
        )

        return {"close_reason": reason, "current_status": "DISPATCHING"}
    except Exception as e:
        db.rollback()
        logger.exception("close_negotiation error for %s: %s", state.ticket_id, e)
        return {"error": str(e)}
    finally:
        db.close()


# ─── Routing ─────────────────────────────────────────────────────────────────


def route_after_interpret(state: TicketState) -> str:
    if state.error is not None:
        return "close"
    if state.close_reason:  # the follow-up schedule ran out
        return "close"
    if state.vendor_intent == "decline":
        return "close"
    if state.quoted_price is not None:
        return "evaluate_quote"
    # Still talking. The cap is what stops an unbounded cycle from tripping
    # LangGraph's recursion limit and killing the ticket with no explanation.
    if state.chat_turns >= MAX_CHAT_TURNS:
        logger.warning(
            "Negotiation on ticket %s hit MAX_CHAT_TURNS — closing", state.ticket_id
        )
        return "close"
    return "post_ai_reply"


def route_after_evaluate(state: TicketState) -> str:
    if state.error is not None:
        return "notify_pm"
    return "confirm_job" if state.auto_approved else "notify_pm"


def route_after_pm_decision(state: TicketState) -> str:
    action = state.pm_negotiation_action
    if action == "accept":
        return "confirm_job"
    if action == "counter" and state.counter_rounds < MAX_COUNTER_ROUNDS:
        return "send_counter"
    if action == "next_vendor":
        return "close"
    # No decision recorded (a misrouted resume) — sit back down rather than
    # guessing what the PM wanted.
    return "await_pm_decision"
