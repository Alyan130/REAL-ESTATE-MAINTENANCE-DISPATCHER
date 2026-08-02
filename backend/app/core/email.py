"""
core/email.py

Email service using the Resend SDK.
"""
from __future__ import annotations

import logging

import resend

from app.config import settings

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


def send_job_offer_email(
    to_email: str,
    vendor_name: str,
    ticket_title: str,
    ticket_summary: str,
    chat_url: str,
) -> None:
    """
    Send a maintenance job offer to a vendor via Resend.

    Fire-and-forget: the negotiation opener calls this after minting the chat
    token, so a mail failure is logged but never raised — it must not roll back
    the job it was announcing.

    `chat_url` is a tokenized link to the vendor chat page. It is built by the
    caller (which holds the token) rather than here, so this module stays a
    renderer and never touches `core/security`.
    """
    job_url = chat_url

    html_body = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2>New job available</h2>
        <p>Hi {vendor_name},</p>
        <p>You've been offered a maintenance job:</p>
        <div style="
            padding: 16px;
            background-color: #f3f4f6;
            border-radius: 6px;
            margin: 16px 0;
        ">
            <p style="margin: 0 0 8px; font-weight: bold;">{ticket_title}</p>
            <p style="margin: 0; color: #374151;">{ticket_summary}</p>
        </div>
        <p>Review the details and submit your quote and availability:</p>
        <a
            href="{job_url}"
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
            View Job &amp; Reply
        </a>
        <p style="margin-top: 24px; font-size: 13px; color: #6b7280;">
            If you're unavailable, no action is needed — the job will be offered
            to another vendor.
        </p>
    </div>
    """

    try:
        resend.Emails.send(
            {
                "from": "Real Estate Dispatcher <onboarding@resend.dev>",
                "to": [to_email],
                "subject": f"New job available: {ticket_title}",
                "html": html_body,
            }
        )
        logger.info("Job offer email sent to %s", to_email)
    except Exception:
        logger.exception("Failed to send job offer email to %s", to_email)


def send_negotiation_message_email(
    to_email: str,
    vendor_name: str,
    ticket_title: str,
    body: str,
    chat_url: str,
) -> None:
    """
    Tell a vendor there's a new message waiting on the job thread.

    The message body is included so the vendor can read it without clicking, but
    replies only happen in the portal — that keeps the whole negotiation in one
    auditable transcript rather than split across an inbox.
    """
    html_body = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2>New message about your job</h2>
        <p>Hi {vendor_name},</p>
        <div style="
            padding: 16px;
            background-color: #f3f4f6;
            border-radius: 6px;
            margin: 16px 0;
        ">
            <p style="margin: 0 0 8px; font-weight: bold;">{ticket_title}</p>
            <p style="margin: 0; color: #374151; white-space: pre-wrap;">{body}</p>
        </div>
        <a
            href="{chat_url}"
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
            Reply
        </a>
    </div>
    """

    try:
        resend.Emails.send(
            {
                "from": "Real Estate Dispatcher <onboarding@resend.dev>",
                "to": [to_email],
                "subject": f"Re: {ticket_title}",
                "html": html_body,
            }
        )
        logger.info("Negotiation message email sent to %s", to_email)
    except Exception:
        logger.exception("Failed to send negotiation message email to %s", to_email)


def send_job_confirmed_email(
    to_email: str,
    vendor_name: str,
    ticket_title: str,
    price: str,
    availability: str,
    property_address: str,
) -> None:
    """
    Confirm an approved job. This is the first message that carries the street
    address — it is deliberately withheld from the chat page until the job is
    APPROVED, since that page is reachable by anyone holding a forwarded link.
    """
    html_body = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2>Job confirmed</h2>
        <p>Hi {vendor_name},</p>
        <p>Your quote has been approved. Here are the details:</p>
        <div style="
            padding: 16px;
            background-color: #f3f4f6;
            border-radius: 6px;
            margin: 16px 0;
        ">
            <p style="margin: 0 0 8px; font-weight: bold;">{ticket_title}</p>
            <p style="margin: 0 0 4px; color: #374151;">Agreed price: {price}</p>
            <p style="margin: 0 0 4px; color: #374151;">Attending: {availability}</p>
            <p style="margin: 0; color: #374151;">Address: {property_address}</p>
        </div>
        <p style="font-size: 13px; color: #6b7280;">
            If anything changes, reply to the job thread.
        </p>
    </div>
    """

    try:
        resend.Emails.send(
            {
                "from": "Real Estate Dispatcher <onboarding@resend.dev>",
                "to": [to_email],
                "subject": f"Job confirmed: {ticket_title}",
                "html": html_body,
            }
        )
        logger.info("Job confirmation email sent to %s", to_email)
    except Exception:
        logger.exception("Failed to send job confirmation email to %s", to_email)
