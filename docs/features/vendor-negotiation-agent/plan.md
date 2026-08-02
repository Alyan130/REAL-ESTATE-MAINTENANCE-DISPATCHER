# Vendor Negotiation Agent — Implementation Plan

## Context

The dispatch agent currently picks a vendor, creates a `PENDING` VendorJob, emails a job offer, and stops. Nothing handles what the vendor says back. `agents/negotiation_agent.py` is a 0-byte file and `TicketState` already reserves `negotiation_messages` / `final_price` / `job_confirmed` / `counter_offered` for it.

This feature builds the missing half: an AI chats with the vendor **inside the platform** via a token-gated link, extracts a price and availability, and either auto-approves it against a PM-set ceiling or hands the PM a decision card. The PM makes every judgment that costs money; the AI does the typing.

Two supporting pieces come with it because the negotiation can't work without them: PM-editable categories carrying `target_price` / `max_price` (there is no auto-approve limit anywhere in the schema today), and Inngest for durable follow-up timers (the backend has no scheduler at all).

**Guiding principle: the AI chats and extracts. The PM decides the money. The AI never commits spending.**

---

## ⚠️ Prerequisites — things YOU must do before implementation starts

### 1. Inngest account and credentials

1. Sign up at [inngest.com](https://inngest.com) (free tier is enough)
2. Create an app, then copy from the dashboard:
   - **Event Key** → `INNGEST_EVENT_KEY`
   - **Signing Key** → `INNGEST_SIGNING_KEY`
3. Add to `backend/.env`:
   ```
   INNGEST_EVENT_KEY=...
   INNGEST_SIGNING_KEY=...
   INNGEST_APP_ID=dispatcher
   INNGEST_DEV=true          # true locally, false in production
   ```
4. **For local dev**, every session needs the Inngest dev server running:
   ```
   npx inngest-cli@latest dev -u http://localhost:8000/api/inngest
   ```
   Without it, timers silently never fire. Its UI also lets you fire a timer by hand — that's how you test "gives up after 2 follow-ups" in 30 seconds instead of 3 days.
5. **For production**, register the Railway app URL in the Inngest dashboard.

### 2. Confirm these are working

- `OPENAI_API_KEY` in `backend/.env` (the intake agent already uses it)
- `REDIS_URL` reachable — the checkpointer is the whole HITL mechanism
- `RESEND_API_KEY` — note `onboarding@resend.dev` only delivers to the Resend account owner's address, so during testing grab the chat URL from the logs rather than the inbox

### 3. One decision left to you

`Notification` rows are written today but **there is no `GET /notifications` endpoint** — nothing reads them. This plan drives the PM decision card off `ticket.status === "QUOTED"` plus `GET /tickets/{id}/negotiation`, so it does **not** depend on notifications. If you want real notification bells, that's a separate small slice — don't block this feature on it.

---

## The flow

```
dispatch picks vendor #1  (already built)
        │
        ▼
open_negotiation ──► mints "job" token, emails chat link,
        │            writes AI opener, arms Inngest timer
        ▼
await_vendor_reply  ⏸ INTERRUPT #1  (state → Redis, process exits)
        │
   ┌────┴─────────────────────────┐
vendor posts                  timer fires
   │                              │
   ▼                        follow-up #1 → #2 → give up
interpret_reply  (LLM: reply + price + availability + intent + confidence)
   │
   ├─ no price yet ──► post_ai_reply ──► back to INTERRUPT #1
   ├─ declined ─────► close_negotiation ──► next vendor
   └─ price found ──► evaluate_quote   (pure Python, no AI)
                          │
              ┌───────────┴────────────┐
        all checks pass          any check fails
              │                         │
              ▼                         ▼
         confirm_job          notify_pm_quote → ⏸ INTERRUPT #2
                                        │
                          PM taps: Accept / Counter $X / Next vendor
                                        │
                              send_counter (MAX 1 ROUND)
                                        └──► back to INTERRUPT #1
```

**Auto-approve is four deterministic checks, no AI:**
```python
price <= category.max_price
and intent == "quote"
and confidence >= 0.8
and not scope_caveats
```
`max_price is None` → never auto-approve. Safe default for a PM who hasn't set prices.

---

## Build order

Each step is independently verifiable. **Do not reorder steps 4 and 5** — with a real LLM in from the start you cannot tell an interrupt bug from a prompt bug, and interrupt bugs look like "the graph is just stuck".

| # | Step | Verify by | Risk |
|---|---|---|---|
| 1 | Categories: table, API, PM screen | PM edits prices, they persist | none |
| 2 | Intake refactor to dynamic categories | file a ticket → still classifies & dispatches | **highest** |
| 3 | `vendor_messages`, job columns, `"job"` token, tokenized email, read-only chat page | dispatch → open link → see the offer | low |
| 4 | Negotiation subgraph with a **stubbed** LLM + both interrupts | send a message, watch it pause and resume | machinery only |
| 5 | Real LLM, `prompts.py`, guards | the conversation reads like a human | medium |
| 6 | Auto-approve + PM decision card + counter | §Verification 5–7 | none |
| 7 | Inngest + follow-ups + next-vendor loop | §Verification 8 via dev UI | low |
| 8 | Demo-mode parity | flip demo on, click the loop | none |

---

## Step 1 — Categories

### New table `category_settings`
`backend/app/models/category_setting.py`

| column | type | notes |
|---|---|---|
| `id` | UUID PK | |
| `pm_id` | UUID FK `users.id` CASCADE, not null | |
| `name` | Text not null | lowercase slug — this is what lands in `tickets.category` / `vendors.categories` |
| `label` | Text not null | PM-editable display name |
| `target_price` | Numeric(10,2) null | negotiation anchor |
| `max_price` | Numeric(10,2) null | **auto-approve ceiling. NULL = never auto-approve** |
| `is_vendor_selectable` | Boolean default true | false for `other` |
| `is_active` | Boolean default true | soft delete |
| `sort_order` | Integer default 0 | |
| `created_at` / `updated_at` | timestamptz | `onupdate=func.now()` |

- `UniqueConstraint("pm_id", "name")` — its btree leads with `pm_id`, so **no separate `pm_id` index** (redundant)
- `CheckConstraint("max_price IS NULL OR target_price IS NULL OR max_price >= target_price")`
- **Soft delete, never hard** — `tickets.category` is free Text with no FK, so deleting a row must not orphan history

### Migration A — `add_category_settings`, `down_revision = "2f7d8c1a6b0e"`

Creates the table, then backfills every existing PM with raw SQL (never import app code into a migration):

```python
op.execute("""
INSERT INTO category_settings
  (id, pm_id, name, label, is_vendor_selectable, is_active, sort_order, created_at, updated_at)
SELECT gen_random_uuid(), u.id, c.name, c.label, c.selectable, true, c.ord, now(), now()
FROM users u
CROSS JOIN (VALUES
  ('plumbing','Plumbing',true,0), ('electrical','Electrical',true,1),
  ('hvac','HVAC',true,2), ('structural','Structural',true,3),
  ('appliance','Appliance',true,4), ('pest','Pest',true,5),
  ('cleaning','Cleaning',true,6), ('other','Other',false,7)
) AS c(name,label,selectable,ord)
WHERE u.role = 'pm'
ON CONFLICT (pm_id, name) DO NOTHING
""")
```

Seed slugs are **byte-identical to the current `Literal` values**, so existing `tickets.category` and `vendors.categories` data needs no migration.

> **Finding: there is no PM signup flow anywhere.** No `/auth/register`, no code that creates a `role="pm"` user — PM rows are inserted by hand. So "seed on signup" has nothing to hang off. Instead: `CategoryService.ensure_seeded(pm_id)` does `SELECT 1 ... LIMIT 1` and runs the same INSERT for that one PM if empty. Called from `GET /categories` and from the intake path.

### API — `backend/app/api/v1/categories.py`, prefix `/categories`

| method | path | dep | codes |
|---|---|---|---|
| GET | `/categories` | `PMUserDep` | 200 (calls `ensure_seeded` first) |
| POST | `/categories` | `PMUserDep` | 201, 400 `DUPLICATE_CATEGORY` |
| PATCH | `/categories/{id}` | `PMUserDep` | 200, 404 |
| DELETE | `/categories/{id}` | `PMUserDep` | 204, 400 if `name == "other"` |

`name` slugified from `label` when omitted. DELETE is a soft delete. **`other` cannot be deleted** — it's the intake fallback and the whole escalation path depends on it existing.

Follow existing shapes: `schemas/categories.py`, `services/category_service.py` (`BaseService`), `repositories/category_repo.py` (`BaseRepository`), provider + `Annotated` dep in `dependencies.py`.

### Frontend
- `frontend/src/app/(pm)/categories/page.tsx` — price editor
- `frontend/src/lib/api/categories.ts`
- `app/(pm)/layout.tsx` — `PM_NAV` += Categories (`Tags` icon from lucide)

---

## Step 2 — Intake refactor for dynamic categories ⚠️ highest risk

`core/categories.py` is imported in exactly **two** backend files, so the blast radius is small — but a mistake here silently stops every ticket from dispatching.

**`backend/app/core/categories.py`** — demoted to the seed list. Delete `TicketCategory`, `VendorCategory`, `VENDOR_CATEGORIES`:
```python
OTHER = "other"
SEED_CATEGORIES: list[tuple[str, str, bool]] = [   # (name, label, vendor_selectable)
    ("plumbing", "Plumbing", True), ..., ("other", "Other", False),
]
```
Its existing docstring already predicted this: *"When the taxonomy later moves to a DB table, this constant is the seed."*

**`backend/app/agentic_AI/output_schemas.py`** — drop the `Literal`:
```python
category: str = Field(description="the category slug, copied exactly from the list in the prompt. use 'other' when nothing fits")
```

**`backend/app/agentic_AI/tools/intake.py`** (currently 0 bytes) — new home for:
```python
def load_allowed_categories(db: Session, pm_id: uuid.UUID) -> list[CategoryOption]:
    """Active categories for this PM, lazily seeded.
    NEVER returns an empty list — falls back to SEED_CATEGORIES."""

def normalize_category(raw: str | None, allowed: list[str]) -> str:
    """Case/whitespace-fold and match. Anything unrecognised → 'other'."""
```

> **The guard everyone forgets:** if `load_allowed_categories` returns `[]`, the prompt lists no categories, the model invents slugs, every one normalizes to `other`, and **every ticket silently stops dispatching**. The `SEED_CATEGORIES` fallback inside that function is not optional.

**`nodes/intake.py::classify_node`** — three edits: pass `state.pm_id` into `load_allowed_categories`, build the text block via `prompts.build_intake_prompt(...)` instead of the inline f-string, and wrap the result in `normalize_category(...)`. The `media_urls` image blocks and the `with_structured_output` call are untouched.

**`backend/app/schemas/vendors.py`** — `categories: list[str] | None`, validation moves to `VendorService.create_invite`.
⚠️ Wire-contract change: an off-list category now returns **400 `UNKNOWN_CATEGORY`** instead of 422. No frontend branch switches on 422 today, so it's safe — log it in `CHANGE-LOG.md`.

**No routing changes needed for unknown categories.** `find_best_vendor` filters `Vendor.categories.any(category)`, no vendor may have `other`, so `select_vendor_node` returns `{}` → `route_after_selection` → `escalate_to_pm_node`. Normalizing to `"other"` is the entire fix.

**Frontend files touched:** `lib/types.ts` (widen `Ticket.category` and `CreateVendorRequest.categories` to `string`), `components/vendors/invite-vendor-modal.tsx`, `app/(pm)/vendors/page.tsx` (coverage-gap calc), `components/tickets/ticket-filters.tsx`, `lib/demo/demo-store.ts`. `status-badge.tsx` and `status.ts` already fall back to the raw string — no change.

---

## Step 3 — Data, token, and the read-only chat page

### Migration B — `add_negotiation`, `down_revision` = Migration A

**`vendor_jobs` new columns:**
```
negotiation_thread_id   Text        null   -- which LangGraph thread owns this
negotiation_opened_at   timestamptz null   -- idempotency guard
last_vendor_message_at  timestamptz null   -- arbiter for the timer-vs-reply race
followups_sent          Integer  not null default 0
counter_rounds          Integer  not null default 0
availability_text       Text        null   -- "Tuesday afternoon"
declined_reason         Text        null
updated_at              timestamptz not null default now() onupdate now()
```
Reuse the **existing** `quote_amount` / `quoted_at` — do not add a parallel price column.

**New table `vendor_messages`:**
```
id             UUID PK
vendor_job_id  UUID FK vendor_jobs.id CASCADE, not null
sender         String(10) not null   -- 'ai' | 'vendor' | 'system'
body           Text not null
extracted      JSONB null            -- {price, availability, intent, confidence, scope_caveats}
created_at     timestamptz not null default now()
Index("ix_vendor_messages_job_created", "vendor_job_id", "created_at")
```

**Why graph state can't hold the transcript:** the 3-day checkpoint TTL is shorter than a P4 negotiation window; the chat page must render history with no live graph; the PM reads it over plain REST; and graph state is per-*ticket* while messages are per-*VendorJob* (vendor #2 runs on the same `TicketState`). `negotiation_messages` in state stays a debug mirror only.

### `ACTIVE_JOB_STATUSES` must change
`agentic_AI/tools/dispatch.py:21`:
```python
ACTIVE_JOB_STATUSES = ["PENDING", "QUOTED", "APPROVED"]
TERMINAL_JOB_STATUSES = ["DECLINED", "EXPIRED", "SUPERSEDED", "COMPLETED"]
```
A vendor who has quoted and is waiting on the PM is committed capacity. Nothing writes `QUOTED` today, so this is a no-op against existing data.

Status machine: `PENDING` (offered, negotiating) → `QUOTED` (PM deciding) → `APPROVED` | `DECLINED` | `EXPIRED` | `SUPERSEDED`.

### The token — stateless JWT, matching the invite pattern

`core/security.py`, one line in `_TOKEN_LIFETIMES`:
```python
"job": timedelta(days=14),
```
Minted as `create_token(user_id=vendor_job.id, role="vendor", token_type="job")` — **`sub` is the `vendor_jobs.id`, not a user id.** No signature change, no stored `chat_token` column. Scoping to one job means a leaked link can't read another ticket, and the job's status is the revocation mechanism.

**Guard sequence** in `services/negotiation_service.py::_authorise_chat`, structured 1:1 against `AuthService._decode_invite`:
```
ExpiredSignatureError        → 410 CHAT_LINK_EXPIRED
PyJWTError                   → 400 INVALID_TOKEN
payload["type"] != "job"     → 400 INVALID_TOKEN      ← type-confusion guard
payload["role"] != "vendor"  → 400 INVALID_TOKEN
sub not a UUID / no row      → 404 NOT_FOUND
job.status in TERMINAL       → 410 CHAT_CLOSED
vendor missing or inactive   → 410 CHAT_CLOSED
```

**Single-use with nothing stored:** the token is valid exactly while `vendor_jobs.status` is non-terminal. PM picks the next vendor → `SUPERSEDED` → link dead. Vendor declines → `DECLINED` → dead. Timers elapse → `EXPIRED` → dead. Job confirmed → `APPROVED` → chat becomes read-only (`can_reply: false`), not 410, because the vendor still needs the details. Re-offering the same vendor later creates a new `VendorJob` row with a new id, so old tokens die with the old row. No watermark column needed.

> **Security fix to include here (one line).** `dependencies.py:47-54` — `get_current_user` never checks `payload["type"]`, so today an **invite token works as a Bearer token**. The new `"job"` token happens to be safe (its `sub` is a job id, so `db.get(User, ...)` returns None), but we're adding a third token type to a system with no type guard. Add:
> ```python
> if payload.get("type") != "login":
>     raise NotAuthenticatedError()
> ```

### Fix the job-offer email
`core/email.py::send_job_offer_email` currently links to `{BASE_URL}/vendor/jobs/{ticket_id}` — **a route that exists on neither frontend nor backend, with no token.** Repoint to `{BASE_URL}/vendor/chat?token={token}`.

### Channel indirection (SMS later — see Notes)
New `backend/app/core/channels.py` with a `NotifyChannel` Protocol, mirroring the `TaskScheduler` Protocol already in `ticket_service.py`. All three new sends go through it. **Wrap every new send in `await asyncio.to_thread(...)`** — `core/email.py`'s functions are sync `def` called from async nodes and block the event loop; one offer email per dispatch was tolerable, a send on every negotiation turn is not. Applying it in one place is why the Protocol exists.

### Vendor chat API — `backend/app/api/v1/vendor_chat.py`, prefix `/vendor-chat`, **no auth dependency**

| method | path | response | codes |
|---|---|---|---|
| GET | `/vendor-chat/{token}` | `VendorChatResponse` | 200, 400, 404, 410 |
| POST | `/vendor-chat/{token}/messages` | `VendorMessageResponse` | **202**, 409 if `can_reply` false, 429 |

Token in the **path**, not the query string, so one `PUBLIC_AUTH_PATHS` entry covers both routes and the token never lands in axios param logging.

**Withhold the street address until `APPROVED`** — an unauthenticated link shouldn't disclose a tenant's address to whoever the email got forwarded to. Property *name* is enough to quote against; the address ships with the confirmation email.

POST writes the message synchronously (so it appears immediately on reload) and schedules the AI asynchronously. Crude rate limit: reject if the same job got a message in the last 2 seconds → 429.

### Frontend chat page
`frontend/src/app/vendor/chat/page.tsx`. Copies `accept-invite/page.tsx` exactly — default export wraps the inner component in `<Suspense>`, inner reads `useSearchParams().get("token")`, missing token → early-return `<Alert tone="danger">`, local `describeChatFailure(error)` switching on stable `code` then `status`. **One deliberate divergence:** accept-invite validates only on submit; the chat page validates on mount via `useAsync(() => getVendorChat(token), [token])`.

Not guarded — `AuthGuard` is applied inside `app/vendor/page.tsx` itself, not in a layout, so a sibling route is unauthenticated by default.

New components: `components/chat/message-bubble.tsx`, `message-thread.tsx` (scroll container + auto-scroll via `useRef` + `useEffect`), `message-composer.tsx` (Enter sends, Shift+Enter newline). No new deps — `motion`, `lucide-react`, and existing UI primitives only.

---

## Step 4 — The subgraph (stubbed LLM)

### Files
- `agentic_AI/nodes/negotiation.py` (new)
- `agentic_AI/tools/negotiation.py` (new — all deterministic logic + DB workers)
- `agentic_AI/agents/negotiation_agent.py` (0 bytes today)

### Nodes

| node | side effects |
|---|---|
| `open_negotiation` | mints token, sends offer email, writes AI opener, arms Inngest timer, persists `negotiation_thread_id` + `negotiation_opened_at`. **Idempotent:** `if job.negotiation_opened_at: return {}` |
| `await_vendor_reply` | **none** — `interrupt()` is statement 1 |
| `interpret_reply` | one LLM call; writes `extracted` onto the vendor's message row |
| `post_ai_reply` | writes AI message, sends email, re-arms timer |
| `evaluate_quote` | writes `quote_amount`/`quoted_at`/`availability_text`, job → `QUOTED`; pure-Python auto-approve check |
| `notify_pm_quote` | `Notification` row, ticket → `QUOTED` |
| `await_pm_decision` | **none** — `interrupt()` is statement 1 |
| `send_counter` | writes counter message, emails, re-arms timer, `counter_rounds += 1` |
| `confirm_job` | job → `APPROVED`, ticket → `APPROVED`, confirmation emails |
| `close_negotiation` | job → `DECLINED`/`EXPIRED`/`SUPERSEDED`, ticket → `DISPATCHING`, emits `negotiation/next-vendor.requested` |

Every node follows the `nodes/dispatch.py` contract exactly: `async def node(state) -> Dict[str, Any]`, own `SessionLocal()`, `try/except → logger.exception + {"error": str(e)}`, `db.rollback()` on write failure, `db.close()` in `finally`, returns only changed keys.

**All side effects for an interrupt live in the node *before* it** — `open_negotiation` before interrupt #1, `notify_pm_quote` before interrupt #2. This is the `notify_pm_node` → `human_approval_node` pattern, and it's mandatory: on resume the interrupt node re-runs from its first line.

### Wiring
```python
builder.add_edge(START, "open_negotiation")
builder.add_edge("open_negotiation", "await_vendor_reply")
builder.add_edge("await_vendor_reply", "interpret_reply")
builder.add_conditional_edges("interpret_reply", route_after_interpret, {
    "post_ai_reply": "post_ai_reply", "evaluate_quote": "evaluate_quote", "close": "close_negotiation",
})
builder.add_edge("post_ai_reply", "await_vendor_reply")        # chat loop
builder.add_conditional_edges("evaluate_quote", route_after_evaluate, {
    "confirm_job": "confirm_job", "notify_pm": "notify_pm_quote",
})
builder.add_edge("notify_pm_quote", "await_pm_decision")
builder.add_conditional_edges("await_pm_decision", route_after_pm_decision, {
    "confirm_job": "confirm_job", "send_counter": "send_counter", "close": "close_negotiation",
})
builder.add_edge("send_counter", "await_vendor_reply")          # counter loop, capped
builder.add_edge("confirm_job", END)
builder.add_edge("close_negotiation", END)

negotiation_graph = builder.compile()          # no checkpointer — matches intake/dispatch
def get_negotiation_graph(checkpointer=None): return builder.compile(checkpointer=checkpointer)
```

> **`MAX_CHAT_TURNS = 12` is not optional.** `post_ai_reply → await_vendor_reply` is an unbounded cycle — a chatty vendor asking questions forever trips LangGraph's default recursion limit of 25 and the ticket dies silently. This is the single most likely runtime failure in the design. Route to `close` above the cap.

**`MAX_COUNTER_ROUNDS = 1` is enforced in three places** (a bug here spends the PM's money): the router, the API guard (409 `COUNTER_LIMIT_REACHED` before the resume is even scheduled), and the `counter_rounds` DB column.

### Splicing into `orchestration_agent.py`
```python
builder.add_node("negotiate", negotiation_graph)
builder.add_edge("dispatch", "negotiate")     # replaces add_edge("dispatch", END), line 130
builder.add_edge("negotiate", END)
```

Two hard rules:
1. **Add the compiled subgraph object directly, never a wrapper function.** On resume, the parent node that invoked the subgraph re-executes — a wrapper's body would re-run on every single vendor message.
2. **Do not splice into `dispatch_graph`.** It compiles with no checkpointer and `_dispatch_from_db` (`ticket_service.py:112`) invokes it directly — an `interrupt()` inside it would raise there.

> **Consequence you must handle.** With negotiation on the parent graph only, `_dispatch_from_db` now ends at `DISPATCHED` and **never negotiates**. Add a `get_post_approval_graph(checkpointer)` in `orchestration_agent.py` (`START → dispatch → negotiate → END`) and rewrite `_dispatch_from_db` to use it inside `with get_checkpointer() as cp:` on thread `f"dispatch-{ticket_id}-{attempt}"`, where `attempt = SELECT count(*) FROM vendor_jobs WHERE ticket_id = ...`. That namespacing is what makes the next-vendor loop work without graph cycles.

### State — extend `TicketState`, don't create a new schema
The subgraph is a node on `StateGraph(TicketState)`; a different schema would need a mapping wrapper, which rule 1 forbids.

```python
active_vendor_job_id: Optional[str] = None
chat_token: Optional[str] = None
quoted_price: Optional[float] = None
quoted_availability: Optional[str] = None
vendor_intent: Optional[str] = None            # quote|question|negotiating|decline|unclear
extraction_confidence: Optional[float] = None
scope_caveats: Optional[bool] = None
counter_rounds: int = 0
chat_turns: int = 0
auto_approved: Optional[bool] = None
auto_approve_reasons: list[str] = Field(default_factory=list)
pm_negotiation_action: Optional[str] = None
pm_counter_price: Optional[float] = None
```

**All overwrite, no reducers** — `open_negotiation` resets every one of them when vendor #2 starts. This is exactly why `counter_rounds` can't reuse the `Annotated[int, operator.add]` trick `dispatch_attempts` uses: an `operator.add` channel **cannot be reset to 0**, only incremented. That's the concrete answer to the per-VendorJob-vs-per-TicketState problem.

`negotiation_messages` keeps its reducer but each dict gains `"vendor_job_id"`. `vendors_contacted` / `dispatch_attempts` keep `operator.add` — a second dispatch pass correctly appends.

### Rebuild-from-DB fallback (the 3-day TTL)
`services/negotiation_service.py`, mirroring `_resume_approval_graph` / `_dispatch_from_db`:

```python
async def _resume_negotiation(job_id, resume_value) -> bool:
    job = ...                                  # read negotiation_thread_id — never guess it
    if not job.negotiation_thread_id: return False
    config = {"configurable": {"thread_id": job.negotiation_thread_id}}
    with get_checkpointer() as cp:
        graph = get_parent_graph(cp) if job.negotiation_thread_id.startswith("ticket-") \
                else get_post_approval_graph(cp)
        snapshot = await graph.aget_state(config)
        if not snapshot or not snapshot.next: return False
        await graph.ainvoke(Command(resume=resume_value), config=config)
        return True
```

Fallback `_negotiate_from_db(job_id)` rebuilds `TicketState` from `VendorJob → Ticket → Property`, hydrates `active_vendor_job_id` / `counter_rounds` / `quoted_price` / messages, and runs `get_negotiation_graph(cp)` on a fresh thread, persisting the new id back to `negotiation_thread_id` first. `open_negotiation`'s `negotiation_opened_at` guard makes re-entry safe — no duplicate offer email.

Useful accident: `CHECKPOINT_TTL` sets `refresh_on_read: True`, so every `aget_state` extends the 3-day window. A PM polling the ticket page keeps the checkpoint alive. Don't depend on it, but it makes the fallback rarer than the raw TTL suggests.

### Interrupt payloads
```python
# #1 await_vendor_reply
interrupt({"kind": "vendor_message", "vendor_job_id": ..., "ticket_id": ..., "round": ...})
#    resume: {"kind": "vendor_message", "message_id": ..., "body": ...}  |  {"kind": "timeout", ...}

# #2 await_pm_decision
interrupt({"kind": "pm_decision", "vendor_job_id": ..., "vendor_name": ..., "quoted_price": ...,
           "availability": ..., "target_price": ..., "max_price": ..., "suggested_counter": ...,
           "counter_rounds_used": ..., "counter_allowed": bool, "reasons": [...]})
#    resume: {"kind": "pm_decision", "action": "accept"|"counter"|"next_vendor", "counter_price": ...}
```
**Each node asserts `resume["kind"]` matches and re-interrupts if not** — the last line of defence against a misrouted resume.

---

## Step 5 — The LLM

### `prompts.py` (0 bytes today — we set the convention)
Templates only; business logic lives in `tools/negotiation.py`, matching the "nodes orchestrate; tools do the DB work" split stated in `tools/dispatch.py`.

```python
NEGOTIATION_SYSTEM_PROMPT = """
You are a maintenance coordinator messaging a contractor on behalf of a property
manager. You are NOT the property manager and you cannot approve spending.

The job
  Title: {ticket_title}
  What the tenant reported: {ticket_summary}
  Trade: {category_label}    Urgency: {priority_label}
  Property: {property_label} Access: {access_note}

Your mandate
  {anchor_clause}
  {counter_clause}

Rules
  1. Never state a dollar figure unless it appears verbatim in "Your mandate"
     above, or the contractor named it first.
  2. Never say yes to a price. Only the property manager approves spending.
  3. Get a firm TOTAL and a day they can attend. Ask for both if either is missing.
  4. If they hedge ("depends what I find", "plus parts"), ask what the total would
     be in the most likely case. Do not accept an open-ended number.
  5. Two or three sentences. Plain text, no markdown, no emoji.
  6. Never mention budgets, ceilings, limits, or that you are an AI.
"""
```

> **`max_price` never enters the prompt.** If the model knows the ceiling it will negotiate to it, or leak it. The ceiling is a Python comparison applied afterwards. `anchor_clause` comes only from `target_price` / the historical median, as soft guidance. `counter_clause` is empty unless the PM authorised a specific figure — in which case it's the only number in the prompt.

`build_mandate(db, job, *, authorised_counter=None) -> Mandate` lives in `tools/negotiation.py` and returns a frozen dataclass, not a string, so it's testable and `prompts.py` stays pure formatting.

### Structured output — `output_schemas.py`, same `Field(description=...)` style
```python
class VendorReplyExtraction(BaseModel):
    reply: str            # 2-3 sentences, plain text
    price: float | None   # firm TOTAL only; null unless they named a number for the whole job
    availability: str | None
    intent: str           # quote | question | negotiating | decline | unclear
    confidence: float     # 0-1: how certain `price` is a firm total, not a rate or estimate
    scope_caveats: bool   # true if conditioned: "depends what I find", "plus parts"
    caveat_note: str = ""
```
`intent` is a plain `str` validated against a frozenset in code — consistent with dropping the category `Literal`.

### Two deterministic guards — this is what stops the AI spending money
```python
def sanitize_reply(draft: str, authorised: set[Decimal]) -> str | None:
    """Return the draft only if every money figure in it is authorised
    ({PM's counter} | {the price the vendor just quoted}). None → caller falls
    back to a canned template. We never send a number nobody approved."""

def validate_extraction(x: VendorReplyExtraction, vendor_text: str) -> VendorReplyExtraction:
    """Zero out `price` when no money token in the VENDOR's own message matches it,
    and force intent='unclear'. Clamp confidence, coerce off-vocabulary intent."""
```
Without the second guard, a model that infers *"sounds like about two hundred"* becomes a $200 auto-approved job.

**Vendor text is untrusted input.** Extraction runs against the strict schema and its output only ever lands in typed fields — never instructions.

---

## Step 6 — Auto-approve, counter, PM decision

All in `tools/negotiation.py`, all pure or read-only, all unit-testable:

```python
AUTO_APPROVE_MIN_CONFIDENCE = 0.8
MAX_COUNTER_ROUNDS = 1
MAX_CHAT_TURNS = 12
MEDIAN_MIN_SAMPLES = 3

def evaluate_auto_approve(*, price, intent, confidence, scope_caveats, max_price) -> AutoApproveDecision
    # returns .approved + .reasons[] — PM-readable strings like
    # "$900.00 is over the $400.00 ceiling", "the price was conditional on what they find"
```

**Historical median** — `VendorJob` has no category, so join through `Ticket`, scope by PM through `Property`:
```python
func.percentile_cont(0.5).within_group(VendorJob.quote_amount.asc())
  .join(Ticket).join(Property)
  .filter(Property.pm_id == pm_id, Ticket.category == category,
          VendorJob.status.in_(["APPROVED", "COMPLETED"]))
```
Only accepted quotes count — a quote the PM rejected is not evidence of the price. Returns `None` below 3 samples so one outlier can't become the anchor. `anchor_price = median or setting.target_price`.

```python
def suggest_counter(*, quoted, anchor, max_price) -> Decimal | None:
    """Nearest $5 between anchor and quote. Never above what they offered,
    never below 85% of anchor (reads as an insult, burns the vendor),
    never above the ceiling. None when there's no anchor."""
```

**Follow-up schedule** scales with priority:
```python
{"P1": [0.5, 1.5], "P2": [4, 12], "P3": [12, 36], "P4": [24, 72]}   # hours
```

### PM API — `backend/app/api/v1/negotiations.py`

| method | path | dep | codes |
|---|---|---|---|
| GET | `/tickets/{id}/negotiation` | `PMUserDep` | 200, 404, 403 |
| POST | `/tickets/{id}/negotiation/decision` | `PMUserDep` + `BackgroundTasks` | **202**, 409 ×2, 403 |

Follows `approve_ticket` precisely: validate synchronously (`_require_pm_owns` via the ticket's property, job must be `QUOTED`, `counter_rounds < MAX`), flip the job status so a double-click 409s, then `schedule(run_pm_decision, ...)` and return 202. `TaskScheduler` Protocol — the service imports no FastAPI.

### PM UI
`components/tickets/negotiation-card.tsx` goes in the **main** column of `app/(pm)/tickets/[id]/page.tsx`, below "What the tenant reported" — a transcript needs the 1.6fr width; the side column is for glanceable facts.

Add a **second** `useAsync` for `getNegotiation(ticketId)` with `.catch(() => null)`, separate from the ticket loader, so a 404 when no negotiation exists doesn't blank the page.

"Counter $X" opens a `Modal` with a prefilled `Input` (`suggested_counter`) and a live client-side warning line, plus explicit copy: **"you get one counter; after this the vendor's answer is final."** The cap is a backend guarantee, but a PM who discovers it by hitting a 409 will feel the product broke.

`lib/status.ts`: add `QUOTED` and `APPROVED` to `STATUS_EXPLANATIONS`; `ACTION_REQUIRED_STATUSES` becomes `["PENDING_APPROVAL", "QUOTED", "NEEDS_ATTENTION", "ERROR"]`.

`lib/use-async.ts`: add an optional `resetKey` to `usePolling`'s options and include it in the effect deps — three lines, backward compatible, no existing call site changes. Chat pages then use `{ intervalMs: 4000, maxTicks: 45, resetKey: lastSentAt }`, so the tick budget restarts every time the user sends. Bumping `maxTicks` to a huge number would be the wrong fix.

`lib/api-client.ts`: `PUBLIC_AUTH_PATHS` += `"/vendor-chat"` (belt-and-braces — our errors are 400/410, not 401, so the interceptor wouldn't fire anyway).

---

## Step 7 — Inngest

`backend/app/core/queue.py`:
```python
inngest_client = inngest.Inngest(app_id=..., event_key=..., signing_key=...,
                                 is_production=not settings.INNGEST_DEV)

async def emit(name: str, data: dict) -> None:
    """Fire-and-forget, same discipline as core/email.py — logs, never raises.
    A timer that fails to arm must not roll back the negotiation that armed it."""
```

`backend/app/jobs/negotiation_jobs.py`:
```python
@inngest_client.create_function(fn_id="negotiation-followup",
    trigger=inngest.TriggerEvent(event="negotiation/followup.scheduled"))
async def negotiation_followup(ctx):
    await ctx.step.sleep_until("wait", datetime.fromisoformat(ctx.event.data["run_at"]))
    await ctx.step.run("nudge", lambda: run_followup(...))
```

`main.py`, after `include_router`:
```python
inngest.fast_api.serve(app, inngest_client, INNGEST_FUNCTIONS, serve_path="/api/inngest")
```
Public but authenticated by Inngest's HMAC — it must **not** sit behind the JWT.

**Why it survives restarts:** `step.sleep_until` hands the clock to Inngest; nothing is held in our process. The container can redeploy mid-sleep. The follow-up **counter** lives in `vendor_jobs.followups_sent` — Postgres, not memory. Each follow-up arms only the *next* one; never arm both up front or you'd have to cancel one.

**Vendor replies use `BackgroundTasks`, not Inngest** — a vendor waiting for a reply shouldn't eat a round trip. Trade-off: no auto-retry on a transient OpenAI failure. Mitigation: `run_vendor_reply` catches, writes a `system` message ("we'll get back to you shortly"), and arms a short follow-up, so failure is visible not silent.

### The reply-vs-timeout race — three mechanisms, all required

**(a) Atomic claim in Postgres.** `run_followup` starts with one conditional UPDATE, aborts on `rowcount == 0`:
```sql
UPDATE vendor_jobs SET followups_sent = followups_sent + 1, updated_at = now()
 WHERE id = :job_id AND status = 'PENDING' AND followups_sent = :expected_round
   AND (last_vendor_message_at IS NULL OR last_vendor_message_at <= :armed_at)
```
Closes every case at once: vendor replied after arming, Inngest retried the step, job already moved on, two timers fired concurrently. The message endpoint's counterpart sets `last_vendor_message_at = now()` in the same transaction as the INSERT.

**(b) A Redis lock around every graph resume.** `RedisSaver` has no per-thread lock, so two concurrent `ainvoke(Command(resume=...))` on one `thread_id` corrupt the checkpoint. `redis` is already a dependency — `SET lock:graph:{thread_id} NX EX 60`. Not acquired → log and drop; the DB claim already decided who wins.

**(c) The `kind` assertion** in each interrupt node (Step 4).

---

## Step 8 — Demo mode

`NEXT_PUBLIC_DEMO_MODE=true` is currently set in `frontend/.env.local`, and any endpoint missing from the adapter's route table hard-404s.

**`fixtures.ts`** — `DEMO_CATEGORIES` (8 seeds with real prices, e.g. plumbing 180/400), `DEMO_CHAT_TOKEN`, and a `DEMO_NEGOTIATION` on the existing `DISPATCHED` ticket with three messages (AI opener, vendor question, AI reply) so the loop is clickable with zero interaction.

**`demo-store.ts`** — `store.categories`, `store.negotiations`; widen `hasVendorFor(category: string | null)`; add `scheduleAiReply` (2.5s, regex `\$\s?(\d+)` → auto-approve or QUOTED), `scheduleCounterReply` (3s, vendor meets in the middle), `scheduleNextVendor` (4s). Extend the existing `scheduleDispatch` to create the negotiation + opener, so the loop is reachable from the approve button that already works.

**`demo-adapter.ts`** — eight routes in the existing `[method, RegExp, handler]` shape. The two `/vendor-chat` handlers are **the only ones that must not call `currentUser(config)`** — that's the point of a token link. Magic tokens mirroring the invite convention: `expired` → 410, `closed` → 410, `bad` → 400. The decision route 409s `COUNTER_LIMIT_REACHED` at `counter_rounds >= 1` so the cap is demonstrable.

---

## Verification

### Manual end-to-end
1. `cd backend && alembic upgrade head` → assert `SELECT pm_id, count(*) FROM category_settings GROUP BY 1` = 8 per PM
2. Set prices on `/categories` (plumbing target 180 / max 400)
3. Start the Inngest dev server (see Prerequisites) — its UI lets you fire timers by hand
4. Tenant files a plumbing ticket → PM approves → grab the chat URL from the logs
5. **Happy path:** incognito, *"I can do it for $180, Tuesday afternoon."* → AI replies → job `QUOTED` → auto-approves (180 ≤ 400) → job + ticket `APPROVED`
6. **PM path:** *"$900"* → ticket `QUOTED`, card shows `"$900.00 is over the $400.00 ceiling"` → counter $400 → text appears in the vendor thread → vendor accepts → **a second counter returns 409**
7. **Caveat path:** *"About $200, but it depends what I find behind the wall."* → must **not** auto-approve despite 200 ≤ 400. This is the test people skip and the one that costs money.
8. **Timeout path:** never reply; advance both timers from the Inngest UI → job `EXPIRED` → ticket back to `DISPATCHING` → vendor #2 offered, vendor #1 excluded
9. **TTL path:** delete the Redis thread key, then send a message → `_negotiate_from_db` rebuilds, **no duplicate offer email**
10. **Race path:** fire the timer and POST a message within the same second → exactly one advances, the other logs a no-op
11. **Token path:** a `login` JWT at `/vendor-chat/{token}` → 400 `INVALID_TOKEN`

### Tests worth writing first
There are zero test conventions today (one 0-byte `backend/tests/__init__.py`), so start with what needs **no fixtures**:

1. **`test_negotiation_rules.py`** — highest value per line. `evaluate_auto_approve` truth table (each of the five failure conditions individually, plus `max_price=None`), `suggest_counter` clamping, `sanitize_reply` rejecting an unauthorised `$650` while accepting `$400` (and handling `£`, `1,200.50`, `200 dollars`), `validate_extraction` zeroing a price the vendor never said, `followup_schedule_for`.
2. **`test_category_normalization.py`** — `"HVAC"` → `hvac`, `" Plumbing "` → `plumbing`, `"roofing"` → `other`, `None` → `other`, empty allowed → `other`.
3. **`test_chat_token.py`** — the security surface. Reject `login` / `invite` / expired tokens, a token for a `SUPERSEDED` job, a valid UUID with no row.
   ⚠️ **Cost warning:** the models use `postgresql.UUID` and `ARRAY`, so **SQLite will not work**. `conftest.py` needs a real Postgres via `TEST_DATABASE_URL`. Budget for that rather than discovering it mid-sprint.

Not worth testing first: graph wiring (run it), prompts (non-deterministic), Inngest handlers (the dev server is a better harness than a mock).

---

## Risks

**Step 2, the intake refactor, is the dangerous one.** An empty allowed-categories list makes every ticket `other` and **silently stops all dispatching** — the `SEED_CATEGORIES` fallback is non-negotiable. On the plus side, `normalize_category` makes a bad model answer non-fatal where today it would raise a Pydantic `ValidationError` inside `with_structured_output`.

**Step 4, the graph splice:**
- `dispatch_graph` must stay interrupt-free, or `_dispatch_from_db` raises
- `_dispatch_from_db` must be upgraded, or the fallback path silently stops at `DISPATCHED`
- Unbounded chat loop → `GraphRecursionError`; `MAX_CHAT_TURNS` is mandatory
- Adding fields to `TicketState` while a checkpoint is paused mid-approval — LangGraph rehydrates missing channels to defaults so it should be clean, and `run_approval`'s `try/except → _mark_needs_attention` is the net. Deploy when nothing is paused if you can.

**Verified as not at risk:** `_require_awaiting_approval` still blocks a double approve after the splice; `Ticket.status` is free `String(30)` so `QUOTED`/`APPROVED` need no migration and `lib/status.ts` already renders them; `find_best_vendor`'s exclusion logic needs no change and already excludes `DECLINED`/`EXPIRED` jobs correctly.

---

## Notes

**SMS is deliberately out of scope.** Vendor notification is email-only (Resend, already built). All new sends go through the `NotifyChannel` Protocol in `core/channels.py` so an SMS adapter is one class later, with no change to the agent's logic — add a `preferred_channel` on `Vendor` and implement the adapter.

Twilio was checked and **cannot work on the free trial**: trial sends only to up to 5 verified numbers with a "Sent from your Twilio trial account" prefix, and — the actual blocker — **trial accounts cannot register for A2P 10DLC**, which is mandatory for any application-to-person SMS to US numbers. Real cost after upgrading: brand registration $4 (sole proprietor) or $48+ (standard), campaign ~$15–17, then $1.50–10/month plus carrier surcharges, with registration taking days to weeks. Not a same-afternoon integration — which is why it's deferred rather than bundled here.

**Also flagged, not fixed here:** `Notification` rows remain write-only until someone builds `GET /notifications`. This feature does not depend on them.
