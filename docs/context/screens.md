# Screens

What needs to be built for the frontend UI, and why each screen exists.

This document describes **purpose and content only** — no colors, themes, or visual direction.

---

## Before You Start: What the Backend Actually Supports Today

The backend is partially built. Screens below are split into two groups:

- **Section A — Buildable now.** Every screen maps to an endpoint that exists and works.
- **Section B — Blocked.** The screen is part of the product vision, but the endpoints don't exist yet. Design can proceed, but the screen cannot be wired up.

Reading this distinction matters: the vendor role has **zero** backend endpoints today. A vendor can be invited and can accept the invite (that's shared auth), but there is nothing for a vendor to log into.

### Ticket status values the UI must handle

The ticket moves through these states. Every list and detail screen must render all of them:

`PENDING_UPLOAD` → `OPEN` → `TRIAGED` → `PENDING_APPROVAL` → `DISPATCHING` → `DISPATCHED` → `CANCELLED` / `NEEDS_ATTENTION` / `ERROR`

Statuses beyond `DISPATCHED` (`QUOTED`, `APPROVED`, `SCHEDULED`, `IN_PROGRESS`, `COMPLETED`, `INVOICED`, `CLOSED`) are declared in the data model but **nothing in the backend sets them yet**. Design for them; expect them to stay empty until the negotiation agent ships.

Three states carry meaning the UI must not flatten into a generic "processing":
- `NEEDS_ATTENTION` — the AI gave up. No vendor was available, or approval processing failed. The PM must act manually.
- `ERROR` — background processing crashed. Distinct from `NEEDS_ATTENTION`; nothing was escalated.
- `PENDING_UPLOAD` — photos are still uploading and the AI hasn't classified the ticket yet. Category, priority, and summary will all be empty for a few seconds.

### Priority values

`P1` (emergency — auto-dispatches, PM never approves it), `P2`, `P3`, `P4`. Priority is set by the AI, not the user.

### Categories

`plumbing`, `electrical`, `hvac`, `structural`, `appliance`, `pest`, `cleaning`, `other`. `other` is an AI catch-all that matches no vendor and always escalates to the PM.

---

# Section A — Buildable Now

## Shared / Unauthenticated

### 1. Login

**Why:** Single entry point for all three roles. There is one login endpoint; the role comes back inside the token and determines where the user lands.

**Content:**
- Email field, password field, submit
- Error states that must be distinguishable to the user:
  - Wrong email or password → one generic message (the backend deliberately does not reveal which was wrong)
  - Account still pending invite acceptance → tell them to check their email for the invite
  - Account disabled → tell them to contact their property manager
- No "sign up" link. Accounts only exist by PM invitation.
- No password reset flow exists in the backend yet.

**After login:** route by role — PM → PM Dashboard, Tenant → Tenant Ticket List, Vendor → nothing exists yet (see Section B).

---

### 2. Accept Invite

**Why:** Tenants and vendors are created by the PM with no password. The invite email links here with a token in the URL. This screen is where the account becomes usable.

**Content:**
- Reads the token from the URL query string — the user never types it
- New password field + confirm password field
- On success the user is logged in immediately and lands on their role's home screen — do not bounce them back to Login
- Error states, each needing its own message:
  - Passwords don't match
  - Token expired → offer to contact the PM for a fresh invite
  - Token superseded (the PM resent the invite, so this older link is dead) → tell them to use the most recent email
  - Invite already accepted → send them to Login instead
  - Invalid/malformed token

---

## Property Manager

### 3. PM Dashboard — All Tickets

**Why:** The PM's home. The core promise of the product is "nothing falls through the cracks" — this is the one place where every ticket across every property is visible.

**Content:**
- List of all tickets across all the PM's properties, newest first
- Per row: title, status, priority, category, the AI's one-line summary, which property, when it was created
- Filters (all three are supported by the backend): by property, by status, by category
- Tickets needing action must be visually separated from the rest. Three groups deserve prominence:
  - `PENDING_APPROVAL` — the PM is the blocker; the AI is literally paused waiting
  - `NEEDS_ATTENTION` — the AI escalated and needs manual intervention
  - `ERROR` — something broke
- Empty state: a PM with no properties gets an empty list. Point them at "Add a property" rather than showing a bare "no tickets."

**Note on the AI summary:** it is pre-formatted as `P{n} {category} — {what happened}`. Display it as-is; don't re-derive it from the category and priority fields.

---

### 4. Ticket Detail (PM view)

**Why:** Where the PM makes the approve/reject decision. This is the single screen the whole product is designed to funnel the PM into — everything else the AI does autonomously.

**Content:**
- Full ticket: title, description as the tenant wrote it, all photos, permission-to-enter flag, property and unit, who reported it, timestamps
- AI triage block: priority, category, plain-English summary
- **Approve / Reject buttons — only when status is exactly `PENDING_APPROVAL`.** Any other status and the backend returns a conflict error. Hide or disable the buttons rather than letting the user hit that error.
- Approve is asynchronous: the API returns immediately with status `DISPATCHING` while vendor selection runs in the background. The screen must reflect "dispatching" right away and then update — the final result (`DISPATCHED` or `NEEDS_ATTENTION`) arrives seconds later with no push mechanism. Plan for polling or a manual refresh.
- Reject is immediate and terminal — the ticket becomes `CANCELLED` with no undo. Confirm before sending.
- `permission_to_enter` matters operationally — a vendor can't enter without it. Don't bury it.
- P1 tickets never show approve/reject. They auto-dispatch during intake. Explain this on the screen so the absence of buttons doesn't read as a bug.
- A manual status override exists in the backend (PM can set any status). Useful for unsticking a `NEEDS_ATTENTION` ticket. Treat it as a secondary/advanced action, not a primary control.

---

### 5. Properties List

**Why:** Properties are the top of the data hierarchy. Tenants attach to properties, tickets attach to properties. A PM cannot invite a tenant until a property exists.

**Content:**
- List of the PM's active properties: name, address, when added
- Add-property action (needs only name and address)
- Delete is a soft delete — the property disappears from the list but its tickets and tenants survive in the database. Word the confirmation accordingly; "delete permanently" would be a lie.
- Empty state is the true first-run state of the entire app. This is step one of onboarding — make it directive.

---

### 6. Property Detail

**Why:** Gives the PM a per-building view — who lives there and what's broken there.

**Content:**
- Property name and address
- Tenants at this property (the tenant list endpoint filters by property)
- Tickets for this property (the ticket list filters by property)
- Invite-a-tenant action, pre-filled with this property

---

### 7. Tenants List

**Why:** The PM's roster of people. Also the only place to see who has and hasn't activated their account.

**Content:**
- All tenants across the PM's properties: name, email, which property, unit number, lease start/end
- **Invite status per tenant — `pending` or `approved`.** A pending tenant cannot log in and cannot file tickets. This is the most operationally important column on the screen.
- Resend invite action, shown only for pending tenants. Resending invalidates the previous link.
- Filter by property
- Deactivate action — disables the tenant profile and their login together. Confirm; there is no reactivate endpoint.

---

### 8. Invite Tenant

**Why:** The only way a tenant account comes into existence.

**Content:**
- Name, email, property (required); unit number, lease start, lease end (optional)
- Property must be selected from the PM's existing properties
- Duplicate email is rejected by the backend — one account per email address, across all roles. Surface this clearly; it's the most likely failure.
- On success the invite email sends automatically. Tell the user that happened.

---

### 9. Vendors List

**Why:** The vendor pool is what the dispatch agent selects from. If it's empty or mis-categorized, dispatch silently fails and every ticket escalates. This screen is effectively the AI's configuration.

**Content:**
- All active vendors: name, email, phone, categories they cover, rating, max concurrent jobs
- Invite status per vendor
- Resend invite for pending vendors
- Deactivate — removes them from AI selection and disables their login
- **Coverage gaps are worth surfacing.** If no active vendor covers `plumbing`, every plumbing ticket will escalate to `NEEDS_ATTENTION`. A PM has no way to know this until tickets start failing. Showing which of the seven vendor categories have no vendor turns a mystery failure into a fixable setup step.

**Why the fields matter (they're not decorative):**
- `categories` — the hard filter. A vendor not tagged `plumbing` will never receive a plumbing job.
- `rating` — the sort key. Highest-rated eligible vendor wins.
- `max_concurrent_jobs` — capacity. A vendor at their limit is skipped entirely.

---

### 10. Invite Vendor

**Why:** Adds a vendor to the dispatch pool.

**Content:**
- Name, email (required); phone, categories, max concurrent jobs (defaults to 3)
- **Categories must be a fixed multi-select**, not free text. Valid values are exactly: `plumbing`, `electrical`, `hvac`, `structural`, `appliance`, `pest`, `cleaning`. Anything else is rejected by the backend. Note that `other` is a ticket-only category and must not appear here.
- Rating is not settable — it defaults to 5.0
- Duplicate email is rejected

---

## Tenant

### 11. Tenant Ticket List

**Why:** The tenant's home. Answers "what's happening with the thing I reported" without them calling anyone — which is the entire point of the tenant experience.

**Content:**
- Only their own tickets, newest first
- Per row: title, status, when submitted
- Prominent "report an issue" action
- **Status must be translated into tenant language.** `DISPATCHING` and `PENDING_APPROVAL` are internal vocabulary. A tenant should read something like "Finding a contractor" and "Waiting on your property manager."
- Do not show the tenant: internal priority codes, vendor names, or the `ERROR` state as raw text.
- Empty state for a new tenant: point them at submitting their first issue.

---

### 12. Submit Ticket

**Why:** The tenant's core action. The target is under 60 seconds on a phone, so this screen should be short.

**Content:**
- Title (required)
- Description (optional, but it's what the AI classifies on — encourage it)
- Photo upload, multiple files allowed
- Permission-to-enter toggle — whether a vendor may enter when the tenant isn't home. This directly affects scheduling, so it belongs on the form rather than in a follow-up.
- **The tenant never picks a category or priority.** The AI does that. Don't add those fields.
- Submission returns immediately with a ticket ID while photos upload and the AI classifies in the background. Confirm receipt right away — don't hold the user on a spinner waiting for classification.
- The ticket will briefly show `PENDING_UPLOAD` with no category or summary. That's expected, not an error.

---

### 13. Tenant Ticket Detail

**Why:** The tenant's record of one issue and its current state.

**Content:**
- Their title, description, and photos
- Current status in plain language
- Submitted and last-updated timestamps
- **Do not expose** the AI summary, priority code, or vendor details — the backend returns those fields on this endpoint, so the frontend must deliberately withhold them. That information is for the PM, not the tenant.

---

# Section B — Blocked on Backend Work

These are real product requirements with no endpoints behind them. Design can proceed; wiring cannot.

### 14. Notifications (PM)

**Blocked:** the `notifications` table exists and the agents write rows to it (`TICKET_PENDING_APPROVAL`, `NO_VENDOR_AVAILABLE`), but there is **no endpoint to read or mark them read**.

**Would contain:** unread count, notification list with type/title/message/timestamp, click-through to the relevant ticket, mark-as-read.

**Why it matters:** right now a PM only discovers a ticket needs approval by opening the dashboard and looking. This is the missing piece of "one-tap approval from my phone."

---

### 15. Vendor Portal — Job List, Job Detail, Quote Submission, Completion Upload, Invoice

**Blocked:** there are **no vendor-facing endpoints at all**. A vendor receives a job-offer email, accepts their invite, and then has nowhere to go. Everything below needs backend work first.

- **Job list** — the vendor's active and past jobs
- **Job detail** — description, photos, property address, permission-to-enter
- **Quote submission** — amount and availability. `VendorJob.quote_amount` and `quoted_at` exist as columns; nothing writes them.
- **Completion upload** — proof photo. `completion_photo` column exists; unused.
- **Invoice submission** — `invoice_url`, `invoice_amount`, `stripe_session_id`, `paid_at` all exist as columns; unused.

---

### 16. PM Quote Review & Vendor Recommendation

**Blocked:** requires the negotiation agent, which is an empty file. No quotes are ever collected, so there is nothing to compare.

**Would contain:** side-by-side quote comparison, the AI's plain-English recommendation, approve/reject on a specific quote.

---

### 17. Auto-Approve Limit per Property

**Blocked:** no field on the property model, no endpoint. Would let quotes under a threshold skip PM review entirely.

---

### 18. Weekly Digest / Reporting

**Blocked:** no aggregation endpoints exist. Would show tickets opened, resolved, pending, and total cost for the week.

---

### 19. Repeat-Issue Alerts

**Blocked:** no detection logic. Would flag a unit with recurring tickets so the PM can schedule a preventive inspection.

---

## Build Order

1. Login + Accept Invite — nothing works without auth
2. Properties → Invite Tenant → Invite Vendor — the setup chain; a PM cannot receive a single ticket until all three exist
3. Tenant Submit Ticket + Ticket List — generates the data everything else displays
4. PM Dashboard + Ticket Detail — closes the loop and makes the AI's work visible

Vendor screens and quote review wait on backend work.
