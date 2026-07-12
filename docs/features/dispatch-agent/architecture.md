## Architecture: Dispatch Agent (HITL Approval)

```mermaid
graph TD
    subgraph API["FastAPI — api/routes/tickets.py"]
        CREATE["POST /tickets<br/>(tenant, photo → BackgroundTask)"]
        APPROVE["POST /tickets/{id}/approve<br/>(PM, guard PENDING_APPROVAL)"]
        REJECT["POST /tickets/{id}/reject<br/>(PM, guard PENDING_APPROVAL)"]
        RUNAPP["_run_approval()<br/>resume → else DB fallback → else escalate"]
        RESUME["_resume_approval_graph()<br/>aget_state().next? → Command(resume)"]
        FALLBACK["_dispatch_from_db()<br/>rebuild state + dispatch_graph"]
    end

    subgraph ORCH["Orchestration Graph (checkpointed, thread=ticket-{id})"]
        INTAKE["intake subgraph<br/>classify + persist_triage"]
        ROUTE{"route_after_intake"}
        NOTIFY["notify_pm_node<br/>status = PENDING_APPROVAL<br/>+ notification"]
        HITL["human_approval_node<br/>⏸️ interrupt() — graph PAUSES<br/>state saved to Redis"]
        DROUTE{"route_on_decision<br/>pm_approved?"}
        CANCEL["cancel_node<br/>status = CANCELLED"]
        DISPATCH["dispatch subgraph"]
    end

    subgraph DGRAPH["Dispatch Subgraph — dispatch_agent.py"]
        SELECT["select_vendor_node<br/>find_best_vendor()"]
        SROUTE{"route_after_selection"}
        JOB["dispatch_job_node<br/>create VendorJob (PENDING)<br/>status = DISPATCHED"]
        ESCALATE["escalate_to_pm_node<br/>status = NEEDS_ATTENTION"]
    end

    subgraph DATA["Data & Integrations"]
        CP[("Redis checkpointer<br/>3-day TTL")]
        VDB[("vendors")]
        VJ[("vendor_jobs")]
        TK[("tickets")]
        NT[("notifications")]
        EMAIL["send_job_offer_email (Resend)"]
        CATS["core/categories.py<br/>Literal vocabulary"]
    end

    CREATE --> INTAKE
    INTAKE --> ROUTE
    ROUTE -->|"P1 (no approval)"| DISPATCH
    ROUTE -->|"P2/P3/P4"| NOTIFY
    ROUTE -->|"error"| ENDX["END"]
    NOTIFY --> HITL
    HITL -. pauses, persists .-> CP

    APPROVE --> RUNAPP
    RUNAPP --> RESUME
    RESUME -->|"live interrupt"| HITL
    RESUME -->|"no checkpoint"| FALLBACK
    RUNAPP -->|"unrecoverable"| ESCALATE
    FALLBACK --> DGRAPH
    REJECT -->|"synchronous"| TK

    HITL --> DROUTE
    DROUTE -->|"approved"| DISPATCH
    DROUTE -->|"rejected"| CANCEL
    DISPATCH -.embeds.-> DGRAPH
    CANCEL --> TK

    SELECT --> SROUTE
    SROUTE -->|"vendor found"| JOB
    SROUTE -->|"none / error"| ESCALATE
    SELECT --> VDB
    SELECT --> VJ
    JOB --> VJ
    JOB --> EMAIL
    JOB --> TK
    ESCALATE --> NT
    ESCALATE --> TK

    CATS -.constrains.-> INTAKE
    CATS -.constrains.-> VDB
```

### Key relationships
- **HITL pause/resume:** for non-P1 tickets the graph pauses at `human_approval_node`'s
  `interrupt()`, persisting to the Redis checkpointer (`ticket-{id}`, 3-day TTL). `/approve`
  resumes the same thread with `Command(resume=...)`; the frozen state (incl. `category`) is
  preserved — no rebuild on the happy path.
- **DB fallback:** if the checkpoint is gone (`aget_state().next` empty), `/approve` rebuilds
  state from the ticket row and runs `dispatch_graph` directly; unrecoverable → `NEEDS_ATTENTION`.
- **Reject is synchronous** (`CANCELLED`), never through the graph — no dependency on a live checkpoint.
- **Guards** (`status == PENDING_APPROVAL`) on both endpoints prevent double-dispatch / stale resume.
- **VendorJob rows** are authoritative for "already contacted"; **shared `Literal`** keeps ticket
  and vendor categories aligned; escalation never fails silently.
