# Real Estate Maintenance Dispatcher

An AI-powered maintenance management system that automates the workflow from tenant issue reporting to ticket triage, property manager approval, vendor selection, and job dispatch.

The system is designed to reduce the manual coordination required for property maintenance while keeping property managers in control of important decisions.

## Highlights

* AI-powered maintenance ticket triage
* Automatic issue classification and priority assessment
* Human-in-the-loop approval for non-emergency tickets
* Priority-based routing for emergency maintenance requests
* Intelligent vendor selection based on service category, rating, and capacity
* Persistent LangGraph workflows using Redis checkpointing
* Automated vendor job creation and email notifications
* Property, tenant, vendor, and maintenance ticket management
* Role-based authentication and invitation-based onboarding
* LangSmith integration for AI workflow tracing and observability

## Problem

Property maintenance often requires a property manager to manually coordinate several steps:

1. Receive a tenant's maintenance request.
2. Understand and classify the issue.
3. Determine its urgency.
4. Find an appropriate vendor.
5. Contact the vendor.
6. Wait for approval or confirmation.
7. Track the resulting job.

This system moves these coordination steps into an automated workflow.

A tenant submits a maintenance issue, the AI analyzes the request, and the system determines the appropriate next step. When human approval is required, the workflow pauses and waits for the property manager instead of continuing autonomously.

## How It Works

```text
Tenant
  |
  | Submit maintenance issue
  | Description + photos
  v
+----------------------+
|    AI Intake Agent   |
|                      |
| - Classify issue     |
| - Determine priority |
| - Generate summary   |
+----------+-----------+
           |
           v
    Priority Router
       /        \
      /          \
    P1          P2 / P3 / P4
     |                |
     |                v
     |        Property Manager
     |             Approval
     |            /       \
     |       Approve      Reject
     |          |            |
     +----------+            v
                |        Cancelled
                v
        Vendor Selection
                |
                v
        Create Vendor Job
                |
                v
        Notify Vendor
```

The workflow is orchestrated with LangGraph, allowing the system to pause during human approval and resume from the saved workflow state.

## AI Workflow

The AI layer is divided into focused components rather than placing the entire process inside a single agent.

### Intake Agent

The intake workflow analyzes the tenant's maintenance request and produces structured information including:

* Maintenance category
* Priority
* AI-generated summary
* Whether property manager approval is required

Supported maintenance categories include:

`plumbing` · `electrical` · `hvac` · `structural` · `appliance` · `pest` · `cleaning` · `other`

Priority levels are:

* P1 — Emergency
* P2
* P3
* P4

### Human Approval

Non-P1 tickets can enter a human approval step before dispatch.

The LangGraph workflow uses an interrupt to pause execution while waiting for the property manager's decision.

Workflow state is persisted using Redis checkpointing.

When the property manager approves the ticket, the workflow resumes using the existing state.

If the checkpoint is unavailable, the system can reconstruct the required state from the database before continuing the dispatch process.

### Vendor Selection

Once a ticket is approved, the dispatch workflow searches for an eligible vendor.

Vendor selection considers:

* Maintenance category
* Vendor availability and capacity
* Vendor rating
* Existing vendor jobs

If a suitable vendor cannot be selected, the ticket can be escalated to the property manager instead of failing silently.

### Vendor Dispatch

After a vendor is selected:

1. A vendor job is created.
2. The ticket is moved to the dispatched state.
3. The configured notification workflow can notify the vendor through email.

## User Roles

### Property Manager

Property managers can:

* Manage properties
* Invite tenants
* Manage vendors
* View maintenance tickets
* Review AI-generated ticket triage
* Approve or reject tickets
* Monitor tickets requiring attention

### Tenant

Tenants can:

* Accept invitations
* Log in
* Submit maintenance issues
* Upload photos
* Specify permission to enter
* View maintenance ticket history
* Track ticket status

### Vendor

The product architecture includes a vendor workflow for receiving jobs, submitting quotes, completing work, and invoicing.

The current repository contains the vendor data model and dispatch functionality, while the complete vendor portal workflow is still under development.

## Architecture

The application is divided into three primary layers:

```text
+---------------------------------------------+
|                  Frontend                   |
|                                             |
|        Next.js + TypeScript + Zustand       |
+----------------------+----------------------+
                       |
                       | HTTP / REST
                       v
+---------------------------------------------+
|                  Backend                    |
|                                             |
|             FastAPI + Pydantic              |
|                                             |
| Auth | Properties | Tenants | Tickets      |
| Vendors | Services | API Routes            |
+----------------------+----------------------+
                       |
              +--------+--------+
              |                 |
              v                 v
+----------------------+  +------------------+
|       AI Layer      |  |    Data Layer    |
|                      |  |                  |
| LangGraph            |  | Supabase/Postgres|
| LangChain            |  | Supabase Storage |
| OpenAI               |  | Redis            |
| LangSmith            |  |                  |
+----------------------+  +------------------+
```

### Workflow Persistence

AI workflows use a Redis-backed LangGraph checkpointer.

For tickets waiting for property manager approval:

```text
LangGraph Workflow
        |
        | interrupt()
        v
Redis Checkpoint
        |
        | Property Manager approves
        v
Resume Workflow
        |
        v
Existing workflow state
        |
        v
Vendor Dispatch
```

This allows long-running AI workflows to behave as stateful processes instead of simple request/response operations.

## Technology Stack

### Frontend

* Next.js
* React
* TypeScript
* Tailwind CSS
* Zustand
* Axios
* Motion
* Lucide React

### Backend

* Python
* FastAPI
* Pydantic
* SQLAlchemy
* Alembic
* PostgreSQL
* JWT authentication
* bcrypt

### AI and Orchestration

* LangGraph
* LangChain
* OpenAI API
* LangSmith

### Infrastructure and Services

* Supabase
* Upstash Redis
* Resend
* Stripe
* Vercel
* Railway
* Docker

## Project Structure

```text
REAL-ESTATE-MAINTENANCE-DISPATCHER/
|
├── backend/
│   ├── app/
│   │   ├── agentic_AI/
│   │   │   ├── agents/
│   │   │   ├── nodes/
│   │   │   ├── tools/
│   │   │   ├── checkpointer.py
│   │   │   ├── output_schemas.py
│   │   │   └── ticket_state.py
│   │   │
│   │   ├── api/
│   │   ├── core/
│   │   ├── models/
│   │   ├── repositories/
│   │   ├── schemas/
│   │   └── services/
│   │
│   ├── migrations/
│   ├── tests/
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   ├── components/
│   │   ├── lib/
│   │   └── stores/
│   │
│   └── package.json
│
├── docs/
│   ├── context/
│   ├── diagrams/
│   ├── features/
│   └── rules/
│
├── .env.example
├── AGENTS.md
├── CLAUDE.md
└── README.md
```

## Getting Started

### Prerequisites

* Python 3.10+
* Node.js
* npm
* PostgreSQL / Supabase
* Redis / Upstash Redis
* OpenAI API key
* LangSmith API key

### Clone the Repository

```bash
git clone https://github.com/Alyan130/REAL-ESTATE-MAINTENANCE-DISPATCHER.git
cd REAL-ESTATE-MAINTENANCE-DISPATCHER
```

### Configure Environment Variables

```bash
cp .env.example .env
```

Configure the required services and credentials defined in `.env.example`, including:

* Supabase / PostgreSQL
* JWT authentication
* Resend
* Supabase Storage
* LangSmith
* Redis
* OpenAI
* Frontend API URL

### Start the Backend

```bash
cd backend

pip install -r requirements.txt

alembic upgrade head

uvicorn app.main:app --reload
```

The API will be available at:

```text
http://localhost:8000
```

### Start the Frontend

In a separate terminal:

```bash
cd frontend

npm install
npm run dev
```

The frontend will be available at:

```text
http://localhost:3000
```

Configure the frontend API URL:

```text
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

## Current Implementation

The current implementation focuses on the core maintenance intake and dispatch workflow:

```text
Tenant submits issue
        |
        v
AI classification
        |
        v
Priority determination
        |
        +----------------+
        |                |
       P1            P2 / P3 / P4
        |                |
        |                v
        |          PM approval
        |                |
        +-------+--------+
                |
                v
        Vendor selection
                |
                v
        Vendor job creation
                |
                v
        Dispatch / escalation
```

The repository also contains the data model and product specifications for later workflow stages, including:

* Vendor quote collection
* Quote comparison
* Vendor negotiation
* Scheduling
* Completion verification
* Invoice submission
* Payment processing
* Weekly reporting
* Repeat-issue detection
* Full vendor portal

These areas are documented in the repository but are not all connected to the current backend workflow.

## Engineering Approach

The system treats AI as part of a larger application workflow rather than as a standalone chatbot.

The architecture combines:

* Deterministic application logic
* Structured LLM outputs
* Explicit workflow state
* Human approval where required
* Persistent workflow checkpoints
* Database-backed state
* Vendor selection rules
* Escalation paths
* AI workflow observability through LangSmith

This approach keeps AI decisions inside a controlled application workflow while maintaining human oversight over important maintenance operations.

## Documentation

Additional technical documentation is available in the `docs` directory.

Key areas include:

* Project context and user stories
* Application screens
* System architecture
* Database design
* AI orchestration
* Dispatch agent
* LangGraph workflow persistence
* Feature specifications
* Implementation plans

See the `docs/features` directory for detailed documentation of individual system components.

## Author

Built by **Alyan Ali** as an AI-powered property maintenance automation system.

## License

No open-source license is currently specified for this repository.
