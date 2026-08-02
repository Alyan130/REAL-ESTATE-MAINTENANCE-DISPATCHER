# End-to-End Test Plan — Intake through Negotiation

Two cases, run against the **real** database, Redis, OpenAI, and LangSmith. Nothing
is mocked: the point is to prove the loop works, not that the code compiles.

Runner: `backend/tests/e2e/test_ticket_lifecycle.py` (pytest + FastAPI `TestClient`).
`TestClient` runs `BackgroundTasks` synchronously on the way out of the response,
which is what makes an async agent pipeline assertable step by step instead of
polled with sleeps.

---

## Preconditions (both cases)

- `backend/.env` has a **real** `OPENAI_API_KEY` (`sk-…`) and a reachable `REDIS_URL`.
- Database seeded — `python -m scripts.seed --reset`.
- Seed facts the cases depend on:
  - plumbing → `target 180 / max 400`
  - `Northgate Plumbing` (rating 4.8) and `Citywide Drains` (4.1) both cover plumbing
  - `tenant@example.com` (Priya, Rosewood Court) and `pm@example.com`, password `demo1234`
- **A photo must be attached.** `ticket_service.py:308` only schedules the graph
  `if files` — with no photo the ticket stays `OPEN` and nothing runs at all.

---

## TC-1 — Full autonomy, PM never touches it

*Proves: P1 skips the approval gate, and a clean quote under the ceiling settles itself.*

- Log in as tenant → `POST /tickets` (multipart, 1 photo) with an unambiguous
  **emergency**: *"Water is pouring through the kitchen ceiling and the light
  fitting is filling up. It's running, not dripping."*
- **Assert intake:** `category == "plumbing"`, `priority == "P1"`,
  `requires_pm_approval is False`, `ai_summary` non-empty.
- **Assert routing:** ticket **never** enters `PENDING_APPROVAL` and no
  `TICKET_PENDING_APPROVAL` notification row is written — `route_after_intake`
  sent it straight to dispatch.
- **Assert dispatch:** one `VendorJob` exists, vendor is `Northgate Plumbing`
  (highest-rated plumber with capacity), job status `PENDING`.
- **Assert negotiation opened:** `negotiation_opened_at` set, one `ai` message in
  `vendor_messages`, chat token mints and resolves.
- Vendor replies via `POST /vendor-chat/{token}/messages`:
  **"$250 all in, I can be there tomorrow morning at 9."**
- **Assert auto-approval:** `evaluate_auto_approve` passes — $250 ≤ $400 ceiling
  **and** `ai_recommendation == "approve"`. Job → `APPROVED`, ticket → `APPROVED`,
  `quote_amount == 250`, `availability_text` non-empty.
- **Assert PM was never asked:** `counter_rounds == 0`, no decision endpoint called.

**Pass = ticket reaches `APPROVED` with zero human input.**

---

## TC-2 — PM approves at every gate

*Proves: both interrupt points pause and resume correctly, and a quote over the
ceiling refuses to settle itself.*

- Same tenant → `POST /tickets` with a **non-emergency**:
  *"The kitchen mixer tap has been dripping for about a week and it's getting
  worse overnight."*
- **Assert intake:** `priority` in P2–P4, `requires_pm_approval is True`.
- **Gate 1 — ticket approval:** ticket sits at `PENDING_APPROVAL`, notification
  row written, graph **paused** (`aget_state(...).next` non-empty).
- Log in as PM → `POST /tickets/{id}/approve`.
- **Assert resume:** the *same* thread resumed (no DB-fallback rebuild — the
  trace must not carry `fallback=True`), dispatch ran, vendor job created.
- Vendor replies: **"It's a bigger job than it looks — $650 including parts,
  Thursday."**
- **Gate 2 — quote approval:** $650 > $400 ceiling, so **no** auto-approval.
  Job → `QUOTED`, ticket stays pre-`APPROVED`, `GET /tickets/{id}/negotiation`
  returns the decision card with a reason naming the ceiling.
- PM → `POST /tickets/{id}/negotiation/decision` `{"action": "accept"}`.
- **Assert final:** job → `APPROVED`, ticket → `APPROVED`, confirmation message
  written to the transcript.

**Pass = ticket reaches `APPROVED` only after two explicit PM decisions.**

---

## Negative assertion (runs inside TC-2)

Before the $650 reply, send **"about $200, but it depends what I find behind the
wall"**. $200 is under the $400 ceiling, so a naive implementation approves it.

- **Assert it does NOT auto-approve** — the model must return
  `ai_recommendation != "approve"` for a hedged quote, and `evaluate_auto_approve`
  must refuse on that basis even though the price passes.

This is the single most expensive failure in the system: it spends real money on
a number nobody committed to.

---

## LangSmith evaluation (both cases)

Every graph run is already tagged with `ticket_id` (added in 0.18.2), so the
report is a metadata query, not manual trace-hunting. After each case:

- Pull all runs where `metadata.ticket_id == <id>`
- Report per case:
  - **LLM call count** (`run_type == "llm"`)
  - **Prompt / completion / total tokens**, summed and per call
  - **Wall-clock latency** per LLM call
  - **Model** used per call
  - **Error count** and any run with `status == "error"`
- Emit a side-by-side table: TC-1 vs TC-2.

Expected shape: TC-1 ≈ 2 LLM calls (1 intake classify + 1 vendor-reply extraction).
TC-2 ≈ 3 (intake + hedged reply + firm reply). A materially higher count means the
graph is looping — worth investigating before it becomes a cost problem.

---

## What this plan does NOT cover

- **Everything after `APPROVED`.** Scheduling, completion, invoicing, and payment
  are not built — nothing writes a status past `APPROVED`.
- **Inngest follow-up timers** — optional at runtime, and chasing a silent vendor
  is a timer test, not a loop test.
- **Real email delivery.** The sandbox sender only reaches the Resend account
  owner; links are read from logs.
