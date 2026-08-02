# Checkpoint

**Branch:** `vendor-agent` · **Last updated:** 2026-08-03
**State:** **The whole loop now runs end to end and is proven.** A tenant's report is classified, sent to a vendor, negotiated by the AI, and either settled automatically or brought to the manager — verified against the real database, real AI, and real pauses. Both end-to-end cases pass.

Feature docs: [`plan.md`](docs/features/vendor-negotiation-agent/plan.md) · [`tasks.md`](docs/features/vendor-negotiation-agent/tasks.md) · [`architecture.md`](docs/features/vendor-negotiation-agent/architecture.md) · [`e2e-test-plan.md`](docs/test-cases/e2e-test-plan.md)

---

## [0.21.0] - 2026-08-03

### Added
- **The full journey has now actually been run, for the first time.** Two automated cases in `backend/tests/e2e/` cover it: an emergency that handles itself with no human involved, and a routine job that stops at both approval points. Run them with `pytest tests/e2e`; ordinary `pytest` skips them, because they cost money and need everything switched on.
- **These tests wipe and refill the database each run, and that is deliberate.** Each run leaves finished jobs behind, and vendors have a job limit — so after a few runs the system correctly picks a *different* plumber and the test fails for a reason that looks like a bug but isn't. Set `E2E_NO_RESEED=1` if you need to inspect what a failed run left behind.
- A cost and speed report (`scripts/langsmith_report.py`) that reads each run's recorded traces. **Written but never run** — it is the one loose end from this session.

### Fixed
- **The workflow could not reach the database on Windows, every single time.** A required setting was applied when a certain file was first loaded, but that file is always loaded *too late* — after the thing it needed to configure had already been created. So it was correct for the next run and useless for the current one. If something works on the second attempt but not the first, suspect this shape of problem.
- **Worth knowing: the previous session's "verified working" check passed only by accident**, because that particular test happened to load things in a lucky order. A green check that passes for an incidental reason is exactly how this survived.
- **The manager's decision card gave the wrong explanation.** It showed the AI's opinion about the quote instead of the actual reason they were being asked. It now says plainly *"$650.00 is over the $400.00 ceiling."*

### Verified — with real money logic, on real data
- **Emergency case:** classified as urgent, skipped the approval step entirely, went to the highest-rated plumber, vendor quoted $250, settled automatically. The manager was never involved. ~82 seconds.
- **Routine case:** stopped and genuinely waited for the manager, resumed on approval, vendor quoted $650, correctly refused to settle itself, manager accepted, job confirmed. ~108 seconds.
- **The test that matters most passed.** A vendor said *"about $200, but it depends what I find behind the wall."* $200 is under the $400 limit, and a careless system approves it. This one refused, because the price was conditional. That is the single most expensive mistake the system could make, and it did not make it.

---

## [0.20.0] - 2026-08-03

### Changed
- **Paused tickets moved from Redis into the main database.** A ticket waiting on a manager is real business information and belongs with the ticket. It also no longer expires — previously a paused ticket was discarded after 3 days, which was shorter than a low-priority job is allowed to take.
- Redis is still used, but only as a traffic light stopping two things resuming the same conversation at once. The existing Upstash account is fine for that.

### Fixed
- **The approval pause could never have worked, on any database.** The wrong version of the storage component was wired in, it was being handed the wrong thing, and its one-time setup was never run. Three faults, all invisible until the system actually ran.

### Verified working
- A workflow was paused, then picked up by a **completely separate connection** and resumed — exactly what happens when a manager approves hours later.

---

## [0.19.1] - 2026-08-03

### Added
- **The AI provider is now a setting, not hard-coded.** Currently running through OpenRouter on `gpt-4o-mini`. Switching provider or model is an `.env` change with no code change.
- **Watch out:** an earlier model choice (`gemma`) returned badly-shaped answers and took over four minutes on a real prompt. If results start looking wrong or slow, check which model is configured before suspecting the code.

---

## [0.19.0] - 2026-08-02

### Removed
- **Demo mode is gone.** The app shows only real database data now.

### Fixed
- **Every invite and vendor link pointed at a domain that doesn't run the app**, so no link generated locally could be opened. They now point at `localhost:3000`.

### Added
- **Invite and vendor chat links are printed in the backend console when running locally.** Test emails never arrive, and the failure is silent by design — the console is the only way to get these links while testing. Switched off automatically outside localhost, since the links grant access.

---

## [0.18.2] - 2026-08-02

### Fixed
- **The AI could never have worked, and nothing was being recorded.** Settings were read into the app's own config but never handed to the operating system, and both the AI and tracing libraries only look there. If a key ever appears to be ignored again, check it is *exported* in `config.py`, not just declared.

### Added
- **Agent runs now arrive labelled**, carrying the ticket, manager, and vendor-job ids as searchable fields — a stalled ticket is one search rather than a scroll. Recovery paths are marked too, which matters because one of them is routine and the other is a warning sign.

---

## [0.18.1] - 2026-08-01

### Fixed
- **The backend could not connect to any Supabase database at all.** The connection string Supabase gives you carries a setting the Postgres driver refuses. Now stripped automatically, so the string can be pasted in as-is.

### Added
- **A seed script (`backend/scripts/seed.py`)** — fills a fresh database, and is **the only way to create the first property manager**, since there is no signup page and invites need an existing manager.
- The test data is shaped to exercise the negotiation: plumbing has a $400 limit so one quote settles itself and a bigger one comes to the manager; structural has no limit and no vendor, so it escalates. Two plumbers exist so "try another vendor" has somewhere to go.

### Changed
- **Test accounts use `@example.com`.** Addresses ending in `.test` are rejected by the API's email checks, so those accounts could never log in.

---

## [0.18.0] - 2026-08-01

### Added
- **The Vendor Negotiation Agent.** After a job goes to a vendor, an AI talks to them through a private link, works out a price and a date, and either confirms the job or brings it to the manager.
- **The manager stays in control of money.** The AI judges whether a quote is firm or vague, but two things are decided by plain code: whether the price is under the manager's limit, and whether the vendor genuinely said that number. **The spending limit is never shown to the AI**, so a vendor cannot talk it into raising it.
- **Vendors get a private link** that opens only their own job and stops working once the job is done or given away. The street address is withheld until the job is confirmed, because that link can be forwarded.

### Fixed
- **An invitation link could be used as a login**, giving full account access. Only proper sign-ins are accepted now.

### Watch out for
- **A conversation is capped at 12 exchanges.** Removing the cap makes long conversations crash silently and the ticket dies with no explanation.
- **A manager gets one counter-offer per vendor**, enforced in three separate places on purpose. Loosening only one would let the same job be countered repeatedly.

---

## Where to start next

1. **Run the report.** `python -m scripts.langsmith_report` after an end-to-end run. It is written and untested — it will tell you what each journey costs in AI calls and time, and whether the conversation is looping more than expected.
2. **Decide about email.** Nothing is reaching anyone: `.test` addresses are rejected by the app's own validation, and `example.com` is rejected by the email provider. Testing real delivery needs a verified domain. Until then, links come from the backend console.
3. **Optional — reminders for silent vendors.** Add Inngest credentials to `backend/.env` and reinstall requirements. Nothing else depends on it.

## Known gaps

- **Nothing happens after a job is approved.** Scheduling, completion, invoicing, and payment are not built — the workflow stops at "approved".
- **When a vendor quotes a price, the AI does not reply in the chat.** The quote goes straight to the decision step, so from the vendor's side their message looks unanswered. Correct as built, but it reads badly.
- Nothing reads the notifications the system writes — there is no notifications screen. The manager's decision card does not rely on them.
- Text messaging is not built. The code is arranged so it is one small addition, but the provider needs a paid account and a registration that takes days.
