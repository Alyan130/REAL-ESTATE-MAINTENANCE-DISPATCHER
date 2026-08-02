# Real Estate Maintenance Dispatcher

## Project Overview
AI-powered maintenance management system for property managers. Automates the full ticket lifecycle — from tenant report to vendor dispatch, quote approval, scheduling, and invoice reconciliation — reducing PM time per ticket from 90 minutes to under 5. Deployed as a dedicated instance per client.

## Data Hierarchy
```
Property Manager
  └── Properties
        └── Tenants
              └── Tickets
                    └── Vendor Jobs
```

## Three Users
- **Property Manager** — approves tickets, reviews quotes, monitors all properties
- **Tenant** — submits issues, tracks status, gets notified
- **Vendor** — receives jobs, submits quotes, uploads completions, gets paid

## What the AI Does
Handles the full loop autonomously: classify ticket → contact vendors → collect quotes → recommend → schedule → verify completion → reconcile invoice. PM only touches the approve/reject step.

---

## Tech Stack

**Frontend:** Next.js 16, Tailwind CSS,Typescript, Zustand for state Managment, Minimal Smooth Tailwaind Animations, Axios for API Handling.

**Backend:** FastAPI, Pydantic, Alembic

**Agents Layer:** LangGraph, LangChain, OpenAI API, Inngest, LangSmith

**Data:** Supabase (Postgres + Storage), Upstash Redis

**Integrations:** Resend, Stripe, Sentry

**Infra:** Vercel, Railway, Docker

---

## User Stories
See [@docs/context/user-story.md](docs/context/user-story.md)

## Rules
- [@docs/rules/coding-conventions.md](docs/rules/coding-conventions.md)
- [@docs/rules/security.md](docs/rules/security.md)
- [@docs/rules/error-handling.md](docs/rules/error-handling.md)

## Design System:
**Use for Consistent UI across all project frontend**
See [@docs/context/design.md](docs/context/design.md)

## Recent Context:
**Always Read These Files Before Starting Any Task**
- [CHECKPOINT.md](CHECKPOINT.md) - **Last Implemenation Details**
- [CHANGE-LOG.md](CHANGE-LOG.md) - **Read Last 2-3 Entries**
