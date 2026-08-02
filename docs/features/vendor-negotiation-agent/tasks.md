# Tasks: Vendor Negotiation Agent

## Prerequisites (user)
- [ ] Create Inngest account and copy Event Key and Signing Key
- [ ] Add INNGEST_EVENT_KEY, INNGEST_SIGNING_KEY, INNGEST_APP_ID, INNGEST_DEV to backend/.env
- [ ] Run `pip install -r requirements.txt` to pick up the new `inngest` dependency
- [ ] Register the production app URL in the Inngest dashboard
- [ ] Confirm OPENAI_API_KEY, REDIS_URL, and RESEND_API_KEY are working
- [ ] Restore the Supabase database — everything below is code-complete but unapplied

## Step 1 — Categories
- [x] Add CategorySetting model (backend/app/models/category_setting.py)
- [x] Write migration A: create category_settings and backfill every existing PM
- [x] Add category repository (repositories/category_repo.py)
- [x] Add CategoryService with ensure_seeded lazy seeding
- [x] Add category Pydantic schemas (schemas/categories.py)
- [x] Add categories router with GET, POST, PATCH, DELETE and wire into v1 router
- [x] Add category service provider and Annotated dep in dependencies.py
- [x] Add categories API client (frontend/src/lib/api/categories.ts)
- [x] Build PM categories price-editor screen
- [x] Add Categories entry to PM_NAV
- [x] Add category demo routes and fixtures
- [ ] Apply migration A — blocked, database unreachable

## Step 2 — Dynamic categories in intake
- [x] Demote core/categories.py to SEED_CATEGORIES and remove the Literal types
- [x] Change IntakeClassification.category to str in output_schemas.py
- [x] Add load_allowed_categories and normalize_category to tools/intake.py
- [x] Add build_intake_prompt to prompts.py
- [x] Rewire classify_node to use the PM category list and normalize the result
- [x] Widen vendor schemas to list[str] and move validation into VendorService
- [x] Widen frontend category types and replace hardcoded category constants
- [x] Title-case unknown slugs in categoryLabel so custom categories render properly
- [x] Mirror the UNKNOWN_CATEGORY check in the demo vendor-invite route
- [x] Write test_category_normalization.py (23 tests)
- [x] Log the vendor-creation 422 to 400 wire change in CHANGE-LOG
- [ ] Confirm a real ticket still classifies and dispatches — blocked, database unreachable

## Step 3 — Negotiation data, token, and chat page
- [x] Add negotiation columns to VendorJob model
- [x] Add VendorMessage model
- [x] Write migration B: vendor_jobs columns and vendor_messages table
- [x] Add QUOTED to ACTIVE_JOB_STATUSES and add TERMINAL_JOB_STATUSES
- [x] Add the job token type to _TOKEN_LIFETIMES
- [x] Add the login token-type guard to get_current_user
- [x] Add chat and negotiation exceptions to exceptions.py
- [x] Add NotifyChannel protocol in core/channels.py with the email adapter
- [x] Repoint send_job_offer_email to the tokenized chat URL
- [x] Move the offer email from dispatch_job_node to open_negotiation (avoids a double send)
- [x] Add NegotiationService with the _authorise_chat guard sequence
- [x] Add vendor_chat router with GET thread and POST message
- [x] Add negotiation API client and wire types and error codes
- [x] Build message-thread and message-composer components
- [x] Build the token-gated vendor chat page
- [x] Add /vendor-chat to PUBLIC_AUTH_PATHS
- [ ] Apply migration B — blocked, database unreachable

## Step 4 — Subgraph
- [x] Add negotiation fields to TicketState (all overwrite, no reducers)
- [x] Build negotiation tools: DB workers and job status transitions
- [x] Build open_negotiation and await_vendor_reply nodes
- [x] Build interpret_reply
- [x] Build post_ai_reply, evaluate_quote, notify_pm_quote, await_pm_decision nodes
- [x] Build send_counter, confirm_job, close_negotiation nodes
- [x] Add the three routing functions with MAX_CHAT_TURNS and MAX_COUNTER_ROUNDS caps
- [x] Wire negotiation_graph and get_negotiation_graph
- [x] Splice negotiate into orchestration_agent and add get_post_approval_graph
- [x] Upgrade _dispatch_from_db to run the post-approval graph with a checkpointer
- [x] Add _resume_negotiation and _negotiate_from_db fallback
- [x] Add the Redis thread lock helper
- [x] Verify both graphs compile and expose the expected nodes

## Step 5 — LLM
- [x] Write NEGOTIATION_SYSTEM_PROMPT and build_negotiation_prompt
- [x] Add the Mandate dataclass and build_mandate (max_price deliberately absent)
- [x] Add VendorReplyExtraction to output_schemas.py
- [x] Wire the real ChatOpenAI structured-output call in interpret_reply
- [x] Add _sanitize_reply money guard
- [x] Add _validate_extraction hallucinated-price guard
- [x] Add transcript injection: pinned price-bearing turns plus the last 4, with relative timestamps

## Step 6 — Auto-approve, counter, PM decision
- [x] Add evaluate_auto_approve (ceiling comparison only — judgment moved to the prompt)
- [x] Add median_quote and anchor selection
- [x] Add suggest_counter with clamping
- [x] Add followup_schedule_for priority table
- [x] Add negotiations router with GET negotiation and POST decision
- [x] Add run_pm_decision background task
- [x] Build the PM negotiation card with Accept, Counter, and Next vendor
- [x] Add the counter modal with the one-round warning
- [x] Add resetKey to usePolling
- [x] Add QUOTED and APPROVED to STATUS_EXPLANATIONS and ACTION_REQUIRED_STATUSES
- [x] Wire the negotiation loader into the PM ticket detail page

## Step 7 — Inngest
- [x] Add inngest to requirements.txt and the four settings to config.py
- [x] Document the Inngest env vars in .env.example
- [x] Add core/queue.py with the lazy client and the fire-and-forget emit
- [x] Add jobs/negotiation_jobs.py with the followup and next-vendor functions
- [x] Serve the Inngest endpoint from main.py, outside the JWT
- [x] Add _run_followup with the atomic Postgres claim
- [x] Set last_vendor_message_at in the same transaction as the message insert
- [x] Wire timer arming into open_negotiation, post_ai_reply, and send_counter
- [x] Degrade cleanly when inngest is absent or unconfigured
- [ ] Fire a timer by hand from the Inngest dev UI — blocked, no credentials

## Step 8 — Demo mode
- [x] Add DEMO_CHAT_TOKEN and DEMO_NEGOTIATIONS to fixtures
- [x] Add negotiations to demo-store with scheduled AI, counter, and next-vendor replies
- [x] Add the four negotiation and chat routes to demo-adapter
- [x] Add the magic chat tokens for expired, closed, and bad
- [x] Add DemoChatLinks to the login screen (the chat has no navigation by design)

## Verification
- [x] Backend imports cleanly and both graphs compile
- [x] test_negotiation_rules.py — 24 tests, no fixtures
- [x] test_chat_token.py — 10 tests, stub session
- [x] Full backend suite green (57 passing)
- [x] Frontend tsc clean, next build passes, /vendor/chat routed
- [x] eslint clean except the pre-existing app-shell.tsx error
- [x] Update CHANGE-LOG.md and CHECKPOINT.md
- [ ] Run migrations and assert eight category rows per PM
- [ ] Verify the happy path auto-approves under the ceiling
- [ ] Verify the over-ceiling path reaches the PM card and one counter succeeds
- [ ] Verify a second counter returns 409
- [ ] Verify a caveated price does not auto-approve
- [ ] Verify the timeout path expires the job and offers the next vendor
- [ ] Verify the TTL fallback rebuilds without a duplicate offer email
- [ ] Verify the reply-versus-timeout race advances exactly once
- [ ] Verify a login token is rejected by the chat endpoint against a real DB
