"""
core/email.py

Email service using the Resend SDK.
"""
from __future__ import annotations

import logging

import resend

from core.config import settings

logger = logging.getLogger(__name__)

resend.api_key = settings.RESEND_API_KEY


def send_invite_email(
    to_email: str,
    name: str,
    role: str,
    token: str,
) -> None:
    """
    Send an invite email via Resend.

    The email contains a CTA link pointing to the frontend accept-invite page
    with the invite JWT as a query parameter.
    """
    invite_url = f"{settings.BASE_URL}/accept-invite?token={token}"
    role_label = role.replace("_", " ").title()

    html_body = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2>You've been invited!</h2>
        <p>Hi {name},</p>
        <p>
            You've been invited to join as a <strong>{role_label}</strong> on the
            Real Estate Maintenance Dispatcher platform.
        </p>
        <p>Click the button below to set up your account:</p>
        <a
            href="{invite_url}"
            style="
                display: inline-block;
                padding: 12px 24px;
                background-color: #2563eb;
                color: #ffffff;
                text-decoration: none;
                border-radius: 6px;
                font-weight: bold;
            "
        >
            Accept Invite
        </a>
        <p style="margin-top: 24px; font-size: 13px; color: #6b7280;">
            This link expires in 48 hours. If you didn't expect this invite,
            you can safely ignore this email.
        </p>
    </div>
    """

    try:
        resend.Emails.send(
            {
                "from": "Real Estate Dispatcher <onboarding@resend.dev>",
                "to": [to_email],
                "subject": f"You're invited to join as a {role_label}",
                "html": html_body,
            }
        )
        logger.info("Invite email sent to %s", to_email)
    except Exception:
        logger.exception("Failed to send invite email to %s", to_email)
