# Dispatch Agent — Implementation Plan

## Context

AI-driven vendor dispatch for approved/P1 maintenance tickets, with a **native
LangGraph human-in-the-loop (HITL)** approval gate. After a ticket is ready to act on
(P1 auto, or PM-approved), the agent selects the single best-matching vendor, creates a
`VendorJob`, and emails the vendor a job offer; if no vendor fits, it escalates to the PM.

The PM-approval gate uses LangGraph's native `interrupt()` / `Command(resume=...)`: the
orchestration graph **pauses** at an approval node (state persisted to the Redis
checkpointer) and the `/approve` endpoint **resumes the same graph**. The paused state
(including `category`) is preserved in the checkpoint, so there is a single path into
dispatch and no state-rebuild is needed on the happy path.

## Approval policy

- **Only P1 skips approval** and auto-dispatches inline.
- **P2 / P3 / P4** pause at the interrupt (status `PENDING_APPROVAL`) until the PM approves
  (→ resume → dispatch) or rejects (→ `CANCELLED`).

## Design decisions

- **Single best vendor**, sequential — not a 3-way fan-out. Matches the singular
  `TicketState` fields (`final_price`, `counter_offered`) and real PM behavior.
- **Native HITL for approvals.** `interrupt()` in a dedicated parent-graph node; resume via
  `Command(resume=...)` on the same `ticket-{id}` thread. Infra already existed (parent graph
  compiled with checkpointer + stable `thread_id`).
- **DB-fallback resume.** `/approve` checks `graph.aget_state(...).next`; if there is no live
  interrupt (checkpoint evicted), it falls back to rebuilding `TicketState` from the DB and
  running `dispatch_graph` directly. On unrecoverable failure → `NEEDS_ATTENTION` + never silent.
- **Checkpoint TTL = 3 days** so a paused approval survives a realistic PM window.
- **Reject is a synchronous `CANCELLED` write** — not routed through the graph; a terminal
  state-set must not depend on a live checkpoint.
- **`VendorJob` rows are the source of truth** for "already contacted" and capacity — not the
  reducer state.
- **Shared category `Literal`** constrains intake output and vendor input so they cannot drift.
- **Retry-on-decline** (next vendor when one declines) is deferred to the Negotiation agent;
  DB-based exclusion + escalation support it now.

## Files

### Agentic layer
- `backend/core/categories.py` — `TicketCategory` / `VendorCategory` `Literal` vocabulary
  (`"other"` is ticket-only, excluded from vendor categories).
- `backend/agentic_AI/tools/dispatch.py` — `find_best_vendor()` (deterministic filter by
  pm/category/active/capacity, ranked by rating; exclusion via `VendorJob` rows) and
  `create_vendor_job()`.
- `backend/agentic_AI/nodes/dispatch.py` — `select_vendor_node`, `route_after_selection`,
  `dispatch_job_node`, `escalate_to_pm_node` (intake node convention).
- `backend/agentic_AI/agents/dispatch_agent.py` — `dispatch_graph`:
  `select_vendor → dispatch_job | escalate_to_pm`.
- `backend/agentic_AI/agents/orchestration_agent.py` — HITL nodes added:
  - `human_approval_node` — dedicated node with `interrupt()` at the top (nothing before it,
    so re-execution on resume is side-effect-free); records the PM decision.
  - `route_on_decision` → `dispatch` | `cancel`.
  - `cancel_node` — sets `CANCELLED` (reached only via resume).
  - Edges: `intake → route_after_intake → {dispatch, notify_pm, END}`;
    `notify_pm → human_approval`; `human_approval → route_on_decision → {dispatch, cancel}`;
    `dispatch → END`, `cancel → END`. P1 path unchanged.
- `backend/agentic_AI/checkpointer.py` — `RedisSaver` configured with a **3-day TTL**
  (`CHECKPOINT_TTL`, minutes) and `refresh_on_read`.
- `backend/agentic_AI/output_schemas.py` — `IntakeClassification.category` → `TicketCategory`.

### API + integrations
- `backend/core/email.py` — `send_job_offer_email()` (Resend, sync, fire-and-forget).
- `backend/schemas/vendors.py` — `CreateVendorRequest.categories` → `list[VendorCategory]`
  (422 on off-vocabulary; no DB migration — column stays `ARRAY(String)`).
- `backend/api/routes/tickets.py`:
  - `_resume_approval_graph(ticket_id, approved)` — `aget_state().next` check → `Command(resume)`
    on `ticket-{id}`; returns whether a live interrupt was resumed.
  - `_dispatch_from_db(ticket_id)` — fallback: rebuild state (hydrate `category`) + `dispatch_graph`.
  - `_mark_needs_attention(ticket_id)` — unrecoverable escalation.
  - `_run_approval(ticket_id)` — background task: resume → else fallback → else escalate.
  - `POST /tickets/{id}/approve` — guard `status == PENDING_APPROVAL`; set `DISPATCHING`;
    background `_run_approval`; 202.
  - `POST /tickets/{id}/reject` — guard `status == PENDING_APPROVAL`; synchronous `CANCELLED`.

## Out of scope
- Retry-on-decline loop (Negotiation agent).
- Vendor quote-submission portal + `VendorJob` `QUOTED`/`DECLINED` transitions (no migration —
  `status` is `String(20)`).
- DB-backed category taxonomy (future upgrade of the `Literal`).
- SMS/Twilio channel.

## Known gap (surfaced, not fixed)
`create_ticket` only triggers the graph when the ticket has a photo (`if file_contents:`).
Photo-less tickets stay `OPEN` and never reach intake/approval/dispatch — a P1 emergency
reported without a photo is dropped. Pre-existing; flagged. P1 verification tickets must include a photo.

## Verification
1. **Static**: `python -c "from agentic_AI.agents.orchestration_agent import get_parent_graph; get_parent_graph()"`.
2. **Pause**: submit a P2 ticket (with photo) → intake runs → assert result carries `__interrupt__`,
   `ticket.status == PENDING_APPROVAL`, PM notification created, checkpoint exists for `ticket-{id}`.
3. **Approve/resume**: `POST /approve` → graph continues into dispatch → `VendorJob(PENDING)`,
   `ticket.status == DISPATCHED`.
4. **Reject**: `POST /reject` → `CANCELLED` synchronously, no `VendorJob`, no graph run.
5. **DB-fallback**: delete the Redis checkpoint for a paused ticket, then `POST /approve` →
   falls back to DB dispatch (or `NEEDS_ATTENTION` if unrecoverable).
6. **Guard**: `POST /approve` on a non-`PENDING_APPROVAL` ticket → 409, no double dispatch.
7. **P1**: P1 ticket dispatches inline with no pause.
8. **TTL**: confirm the checkpoint carries a ~3-day expiry.
9. **Vendor constraint**: `POST /auth/invites/vendors` `["HVAC"]` → 422; `["hvac"]` → 201.
