"""
app/services/invites.py

Issuing an invite is the same four steps for tenants and vendors, on both the
first send and every resend, so it lives in one place.
"""
from __future__ import annotations

from app.core.email import send_invite_email
from app.core.security import create_token, decode_token
from app.models.user import User


def issue_invite(user: User, name: str) -> None:
    """
    Mint an invite token, stamp its `iat` on the user, and email the link.

    The stamp is what retires older links: `accept_invite` rejects any token
    issued before `last_invite_iat`, so a resend invalidates every earlier email.
    The caller must commit — this only stages the change.
    """
    token = create_token(user_id=user.id, role=user.role, token_type="invite")

    payload = decode_token(token)
    iat_raw = payload.get("iat")
    try:
        user.last_invite_iat = int(iat_raw) if iat_raw is not None else None
    except (TypeError, ValueError):
        user.last_invite_iat = None

    # Fire-and-forget: send_invite_email swallows and logs its own failures, so a
    # mail outage never rolls back the account it just created.
    send_invite_email(to_email=user.email, name=name, role=user.role, token=token)
