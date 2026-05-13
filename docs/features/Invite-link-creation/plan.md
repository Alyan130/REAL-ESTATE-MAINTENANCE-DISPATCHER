# Phase 2 — PM Dashboard: Invite Creation & User Management

Enable PMs to create tenant/vendor records and trigger invite emails via Resend. Track invite status (`pending` / `approved`) across all user types.

## User Review Required

> [!IMPORTANT]
> **Tenant `property_id` requirement**: The existing `Tenant` model requires a `property_id` foreign key. The `POST /pm/tenants` endpoint will therefore also require a `property_id` in the request body so the tenant can be linked to a property. This is necessary because the DB schema enforces a non-nullable FK constraint on `tenants.property_id`.

> [!IMPORTANT]
> **Resend "from" address**: Resend requires a verified domain for the `from` address. The plan uses `noreply@resend.dev` (Resend's test domain) for development. You will need to verify your own domain before going to production.

## Proposed Changes

### Configuration
#### [MODIFY] [requirements.txt](file:///d:/next_js/projects/REAL-ESTATE-MAINTENANCE-DISPATCHER/backend/requirements.txt)
- Add `resend` Python SDK

#### [MODIFY] [.env](file:///d:/next_js/projects/REAL-ESTATE-MAINTENANCE-DISPATCHER/backend/.env)
- Add `RESEND_API_KEY` and `BASE_URL` (frontend URL for invite links)

#### [MODIFY] [config.py](file:///d:/next_js/projects/REAL-ESTATE-MAINTENANCE-DISPATCHER/backend/core/config.py)
- Add `RESEND_API_KEY` and `BASE_URL` to `Settings`

---

### Auth Dependencies
#### [MODIFY] [deps.py](file:///d:/next_js/projects/REAL-ESTATE-MAINTENANCE-DISPATCHER/backend/api/deps.py)
- Add `require_pm` dependency: wraps `get_current_user` and raises `403` if `user.role != "pm"`. Creates `PMUserDep` type alias.

---

### Email Service
#### [NEW] [email.py](file:///d:/next_js/projects/REAL-ESTATE-MAINTENANCE-DISPATCHER/backend/core/email.py)
- `send_invite_email(to_email, name, role, token)`: Sends invite via Resend API
- Email contains a CTA link: `{BASE_URL}/accept-invite?token={token}`
- Uses `resend.Emails.send()` with HTML body
- Wraps call in try/except for graceful error handling (logs failure, does not crash request)

---

### PM Routes
#### [NEW] [pm.py](file:///d:/next_js/projects/REAL-ESTATE-MAINTENANCE-DISPATCHER/backend/api/routes/pm.py)
All endpoints protected by `require_pm`.

**`POST /pm/tenants`**
- Accepts: `name`, `email`, `property_id`, `unit_number`, `lease_start`, `lease_end`
- Flow: Create `User(role="tenant", invite_status="pending")` → Create `Tenant` record linked to user + property → Generate invite JWT (48h) → Send invite email → Return tenant response

**`POST /pm/vendors`**
- Accepts: `name`, `email`, `phone`, `categories`, `max_concurrent_jobs`
- Flow: Create `User(role="vendor", invite_status="pending")` → Create `Vendor` record linked to PM → Generate invite JWT (48h) → Send invite email → Return vendor response

**`GET /pm/tenants`**
- Returns all tenant records with their user's `invite_status` and basic info

**`GET /pm/vendors`**
- Returns all vendor records with their user's `invite_status` and basic info

---

### App Entry Point
#### [MODIFY] [main.py](file:///d:/next_js/projects/REAL-ESTATE-MAINTENANCE-DISPATCHER/backend/main.py)
- Register `pm.router`

---

## Verification Plan

### Manual Verification
- Start the FastAPI server with `fastapi dev backend/main.py`
- Use Swagger UI to test all endpoints:
  1. Login as PM → get token
  2. Create tenant → confirm DB record + email delivered
  3. Create vendor → confirm DB record + email delivered
  4. List tenants/vendors → verify `invite_status` visible
  5. Attempt with non-PM token → verify `403`
