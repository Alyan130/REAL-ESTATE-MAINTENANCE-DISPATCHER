"""
End-to-end: intake through negotiation, against live services.

See docs/test-cases/e2e-test-plan.md. Two cases:

  TC-1  a P1 emergency skips the approval gate and a clean quote under the
        ceiling settles itself — zero human input.
  TC-2  a routine ticket stops at both human gates, and a quote over the ceiling
        refuses to settle itself.

Run:  python -m pytest tests/e2e -v -s

Each case asserts stage by stage rather than only on the final status, because
"ticket reached APPROVED" is true of both a working pipeline and one that skipped
half of it.
"""
from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.agentic_AI.tools.negotiation import mint_chat_token
from app.database import SessionLocal
from app.models.notification import Notification
from app.models.ticket import Ticket
from app.models.vendor import Vendor
from app.models.vendor_job import VendorJob
from app.models.vendor_message import VendorMessage
from tests.e2e.conftest import record_ticket, submit_ticket

pytestmark = pytest.mark.e2e


# ─── Helpers ─────────────────────────────────────────────────────────────────


def fresh(ticket_id: uuid.UUID) -> Ticket:
    """Re-read the ticket on a new session — background tasks wrote it elsewhere."""
    db: Session = SessionLocal()
    try:
        db.expire_all()
        return db.get(Ticket, ticket_id)
    finally:
        db.close()


def job_for(ticket_id: uuid.UUID) -> VendorJob | None:
    db: Session = SessionLocal()
    try:
        db.expire_all()
        return (
            db.query(VendorJob)
            .filter(VendorJob.ticket_id == ticket_id)
            .order_by(VendorJob.created_at.desc())
            .first()
        )
    finally:
        db.close()


def messages_for(job_id: uuid.UUID) -> list[VendorMessage]:
    db: Session = SessionLocal()
    try:
        return (
            db.query(VendorMessage)
            .filter(VendorMessage.vendor_job_id == job_id)
            .order_by(VendorMessage.created_at)
            .all()
        )
    finally:
        db.close()


def vendor_name(vendor_id: uuid.UUID) -> str:
    db: Session = SessionLocal()
    try:
        return db.get(Vendor, vendor_id).name
    finally:
        db.close()


def approval_notifications(ticket_id: uuid.UUID) -> int:
    """How many 'needs your approval' notifications this ticket produced."""
    db: Session = SessionLocal()
    try:
        return (
            db.query(Notification)
            .filter(Notification.type == "TICKET_PENDING_APPROVAL")
            .filter(Notification.message.contains(str(ticket_id)[:8]))
            .count()
        )
    finally:
        db.close()


def vendor_says(client: TestClient, job: VendorJob, body: str) -> None:
    """Post a vendor message through the real token-gated endpoint."""
    token = mint_chat_token(job.id)
    r = client.post(f"/vendor-chat/{token}/messages", json={"body": body})
    assert r.status_code == 202, r.text


def show(label: str, ticket: Ticket, job: VendorJob | None = None) -> None:
    line = f"  [{label}] ticket={ticket.status}"
    if ticket.category:
        line += f" {ticket.priority}/{ticket.category}"
    if job:
        line += f" | job={job.status} quote={job.quote_amount} avail={job.availability_text!r}"
    print(line)


# ─── TC-1 ────────────────────────────────────────────────────────────────────


def test_tc1_full_autonomy(client: TestClient, tenant_auth, pm_auth):
    """A P1 emergency dispatches itself and a $250 quote settles under the $400 ceiling."""
    print("\nTC-1 — full autonomy")

    ticket_id = submit_ticket(
        client,
        tenant_auth,
        title="Water pouring through the kitchen ceiling",
        description=(
            "Water is pouring through the kitchen ceiling and the light fitting "
            "is filling up. It's running, not dripping."
        ),
    )
    record_ticket("TC-1", ticket_id)
    print(f"  ticket {ticket_id}")

    # ── intake ──
    ticket = fresh(ticket_id)
    show("intake", ticket)
    assert ticket.status != "ERROR", "intake crashed — check the LLM key and logs"
    assert ticket.category == "plumbing", f"got {ticket.category!r}"
    assert ticket.priority == "P1", f"got {ticket.priority!r}"
    assert ticket.ai_summary, "no summary written"

    # ── routing: the approval gate must have been skipped entirely ──
    assert ticket.status != "PENDING_APPROVAL", "P1 must not wait for approval"
    assert approval_notifications(ticket_id) == 0, "P1 raised an approval notification"

    # ── dispatch ──
    job = job_for(ticket_id)
    assert job is not None, "no VendorJob — dispatch did not run"
    assert vendor_name(job.vendor_id) == "Northgate Plumbing", (
        f"expected the highest-rated plumber, got {vendor_name(job.vendor_id)}"
    )
    show("dispatch", ticket, job)

    # ── negotiation opened ──
    assert job.negotiation_opened_at is not None, "negotiation never opened"
    opening = messages_for(job.id)
    assert len(opening) == 1 and opening[0].sender == "ai", (
        f"expected one AI opener, got {[(m.sender) for m in opening]}"
    )
    print(f"  [opener] {opening[0].body[:88]}")

    # the chat link the vendor receives must resolve
    r = client.get(f"/vendor-chat/{mint_chat_token(job.id)}")
    assert r.status_code == 200, r.text
    chat = r.json()
    assert chat["can_reply"] is True
    # the address is withheld until the job is confirmed
    assert "Rosewood Court" in chat["property_label"]
    assert "14 Rosewood" not in chat["property_label"]

    # ── vendor quotes under the ceiling ──
    vendor_says(client, job, "$250 all in, I can be there tomorrow morning at 9.")

    job = job_for(ticket_id)
    ticket = fresh(ticket_id)
    show("after quote", ticket, job)
    for m in messages_for(job.id)[1:]:
        print(f"    {m.sender:6} {m.body[:80]}")

    # ── auto-approval ──
    assert job.quote_amount is not None, "no quote recorded"
    assert float(job.quote_amount) == 250.0, f"got {job.quote_amount}"
    assert job.availability_text, "availability not captured"
    assert job.status == "APPROVED", f"job did not auto-approve — status {job.status}"
    assert ticket.status == "APPROVED", f"ticket did not auto-approve — {ticket.status}"

    # ── the PM was never involved ──
    assert job.counter_rounds == 0
    r = client.get(f"/tickets/{ticket_id}/negotiation", headers=pm_auth)
    assert r.status_code == 200
    assert r.json()["awaiting_decision"] is False, "PM was asked to decide"

    print("  PASS — APPROVED with zero human input")


# ─── TC-2 ────────────────────────────────────────────────────────────────────


def test_tc2_pm_approves_at_every_gate(client: TestClient, tenant_auth, pm_auth):
    """Both interrupts pause and resume, and a hedged/over-ceiling quote refuses to settle."""
    print("\nTC-2 — PM at both gates")

    ticket_id = submit_ticket(
        client,
        tenant_auth,
        title="Kitchen mixer tap dripping",
        description=(
            "The kitchen mixer tap has been dripping for about a week and it's "
            "getting worse overnight."
        ),
    )
    record_ticket("TC-2", ticket_id)
    print(f"  ticket {ticket_id}")

    # ── intake ──
    ticket = fresh(ticket_id)
    show("intake", ticket)
    assert ticket.status != "ERROR", "intake crashed"
    assert ticket.priority in {"P2", "P3", "P4"}, f"got {ticket.priority!r} — should not be P1"

    # ── gate 1: paused at PENDING_APPROVAL ──
    assert ticket.status == "PENDING_APPROVAL", f"got {ticket.status}"
    assert job_for(ticket_id) is None, "dispatched before the PM approved"

    import asyncio

    from app.agentic_AI.agents.orchestration_agent import get_parent_graph
    from app.agentic_AI.checkpointer import get_checkpointer

    async def paused_at() -> tuple:
        async with get_checkpointer() as cp:
            snap = await get_parent_graph(cp).aget_state(
                {"configurable": {"thread_id": f"ticket-{ticket_id}"}}
            )
            return snap.next if snap else ()

    assert asyncio.run(paused_at()), "graph is not paused — the interrupt did not hold"
    print("  [gate 1] paused at the approval interrupt")

    # ── PM approves ──
    r = client.post(f"/tickets/{ticket_id}/approve", headers=pm_auth)
    assert r.status_code == 202, r.text

    job = job_for(ticket_id)
    assert job is not None, "approval did not dispatch"
    ticket = fresh(ticket_id)
    show("after approve", ticket, job)
    assert job.negotiation_opened_at is not None, "negotiation never opened"

    # ── the negative assertion: a hedged quote under the ceiling ──
    # $200 is comfortably under $400. A naive implementation approves it. The
    # model must refuse because the number is conditional, and this is the single
    # most expensive failure mode in the system.
    vendor_says(
        client, job, "About $200, but it depends what I find behind the wall."
    )

    job = job_for(ticket_id)
    ticket = fresh(ticket_id)
    show("after hedge", ticket, job)
    hedge = [m for m in messages_for(job.id) if m.extracted][-1]
    print(f"    extracted: price={hedge.extracted.get('price')} "
          f"firm={hedge.extracted.get('is_firm_total')} "
          f"rec={hedge.extracted.get('recommendation')!r}")
    print(f"    reasoning: {hedge.extracted.get('reasoning', '')[:88]}")

    assert job.status != "APPROVED", (
        "A HEDGED QUOTE AUTO-APPROVED. This spends real money on a number nobody "
        "committed to — the most expensive failure in the system."
    )
    assert ticket.status != "APPROVED", "ticket approved on a hedged quote"

    # ── vendor firms up, over the ceiling ──
    vendor_says(
        client, job, "It's a bigger job than it looks — $650 including parts, Thursday."
    )

    job = job_for(ticket_id)
    ticket = fresh(ticket_id)
    show("after $650", ticket, job)

    # ── gate 2: over the ceiling, so it must come to the PM ──
    assert job.status == "QUOTED", f"expected QUOTED, got {job.status}"
    assert ticket.status != "APPROVED", "$650 auto-approved over a $400 ceiling"

    r = client.get(f"/tickets/{ticket_id}/negotiation", headers=pm_auth)
    assert r.status_code == 200, r.text
    card = r.json()
    print(f"  [gate 2] card: quoted={card['quoted_price']} ceiling={card['max_price']} "
          f"suggested={card['suggested_counter']}")
    print(f"           reason: {card['decision_reason']}")
    assert card["awaiting_decision"] is True
    assert float(card["quoted_price"]) == 650.0
    assert card["counter_allowed"] is True

    # ── PM accepts ──
    r = client.post(
        f"/tickets/{ticket_id}/negotiation/decision",
        headers=pm_auth,
        json={"action": "accept"},
    )
    assert r.status_code == 202, r.text

    job = job_for(ticket_id)
    ticket = fresh(ticket_id)
    show("final", ticket, job)
    assert job.status == "APPROVED", f"job did not approve — {job.status}"
    assert ticket.status == "APPROVED", f"ticket did not approve — {ticket.status}"
    assert any(m.sender == "system" for m in messages_for(job.id)), (
        "no confirmation written to the transcript"
    )

    print("  PASS — APPROVED only after two explicit PM decisions")
