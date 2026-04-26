# Phase 3 — Invite Acceptance & Resend INVITE Flow

Allow users to accept their invites by setting a password. Also allows Property Managers to resend invites.

## User Review Required

> [!IMPORTANT]
> **Token Invalidation**: The requirement states "Old token for that user is effectively invalidated by the new one being issued". Since JWTs are inherently stateless, the only way to reliably invalidate an old token when a new one is issued (without a stateful session store/Redis) is to store a reference to the latest token in the database.
> **Decision**: I propose adding a `last_invite_iat` (Integer, tracking the `iat` timestamp of the latest invite) to the `User` table. When `decode_token` or the accept logic runs, it will check if the token's `iat` matches the user's `last_invite_iat`. If a new invite is sent, `last_invite_iat` is updated, making the old token invalid. An Alembic migration will be created for this.

## Proposed Changes

### Database Schema
#### [MODIFY] [backend/models/user.py](file:///d:/next_js/projects/REAL-ESTATE-MAINTENANCE-DISPATCHER/backend/models/user.py)
- Add `last_invite_iat: Mapped[int | None] = mapped_column(Integer, nullable=True)` to track the timestamp of the latest invite token.
- Generate an Alembic migration.

---

### Endpoints
#### [MODIFY] [backend/api/routes/auth.py](file:///d:/next_js/projects/REAL-ESTATE-MAINTENANCE-DISPATCHER/backend/api/routes/auth.py)
**`POST /auth/accept-invite`**
- Accepts: `token`, `password`, `confirm_password` (`AcceptInviteRequest` model).
- Validation:
  - If `password != confirm_password`, returns `400`.
  - Try `decode_token(token)`. If `jwt.ExpiredSignatureError` is caught, returns `410 Gone`.
  - Check payload `type == "invite"`.
  - Fetch user by payload `sub`. If `user.invite_status != "pending"`, return `400` (already accepted).
  - **Invalidation Check**: If `payload["iat"] < user.last_invite_iat`, return `410 Gone` (token was superseded).
- Success:
  - Hash password via `hash_password(password)`.
  - Set `user.password_hash = ...`, `user.invite_status = "approved"`, `user.last_invite_iat = None`.
  - Commit DB.
  - Return a new `login` JWT via `create_token(..., token_type="login")`.

#### [MODIFY] [backend/api/routes/pm.py](file:///d:/next_js/projects/REAL-ESTATE-MAINTENANCE-DISPATCHER/backend/api/routes/pm.py)
**`POST /pm/tenants/{id}/resend-invite`**
- Protected: `require_pm`.
- Fetch `Tenant` by ID ensuring it belongs to PM's properties.
- Fetch linked `User`. Ensure `invite_status == 'pending'`.
- Generate new token via `create_token(..., token_type="invite")`.
- Extract `iat` from token and update `user.last_invite_iat`.
- Send email via `send_invite_email(...)`.
- Return `200 OK`.

**`POST /pm/vendors/{id}/resend-invite`**
- Same logic as above, but fetching `Vendor`.

*(Note: We will also need to update the creation endpoints in `pm.py` to set `user.last_invite_iat` upon their initial invite creation).*

---

## Verification Plan

### Automated Tests
- In `tests/test_auth.py`:
  - Test `accept-invite` flow with valid token -> returns login token.
  - Test `accept-invite` with expired token -> returns `410`.
  - Test `accept-invite` with superseded token (old `iat`) -> returns `410`.
- In `tests/test_pm.py` (new):
  - Test `resend-invite` for tenant & vendor (updates `last_invite_iat` and sends email).
