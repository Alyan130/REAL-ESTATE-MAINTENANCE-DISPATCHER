"""
app/services/invites.py

Issuing an invite is the same four steps for tenants and vendors, on both the
first send and every resend, so it lives in one place.
"""
from __future__ import annotations

import logging

from app.config import settings
from app.core.email import send_invite_email
from app.core.security import create_token, decode_token
from app.models.user import User

logger = logging.getLogger(__name__)


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

    # Local only. Resend's sandbox sender (onboarding@resend.dev) delivers to the
    # Resend account owner and silently drops everything else, so an invite to a
    # test address never arrives and the failure is invisible — send_invite_email
    # catches its own errors by design. Without this line there is no way to
    # accept an invite while testing. Gated on BASE_URL being localhost so a
    # deployed environment never writes an account-granting link to its logs,
    # which `docs/rules/security.md` forbids.
    if "localhost" in settings.BASE_URL or "127.0.0.1" in settings.BASE_URL:
        logger.info(
            "[dev] invite link for %s: %s/accept-invite?token=%s",
            user.email,
            settings.BASE_URL,
            token,
        )
