# LangGraph Intake and Orchestration Implementation

Implement the PropFlow AI system's intake subgraph and parent graph using a shared state approach.

## Proposed Changes

### backend/agentic_AI
#### [NEW] nodes/intake/__init__.py
Empty init file.

#### [NEW] output_schemas.py
Provides shared Pydantic models (such as `IntakeClassification`) for LLM structured output schemas.

#### [NEW] nodes/intake.py
Implement `classify_node` and `persist_triage_node`. 
- `classify_node`: Fetches ticket data, directly utilizes public `media_urls` from the DB for image analysis, and uses OpenAI structured output for triage.
- `persist_triage_node`: Updates the database with the triaged category, priority, and summary.

#### [NEW] agents/intake_agent.py
Constructs the intake subgraph wiring `START -> classify_node -> persist_triage_node -> END`. 

#### [NEW] agents/orchestration_agent.py
Constructs the parent graph. Adds the intake subgraph, `notify_pm_node`, `trigger_dispatch_node` (stub). Defines routing logic. (Cancel node stub removed per request).

### backend/api/routes
#### [MODIFY] tickets.py
Implement `_invoke_graph` to instantiate and execute the async parent graph. Update `_process_ticket_submission` to construct the initial `TicketState` and call `_invoke_graph` via `asyncio.run()`.
