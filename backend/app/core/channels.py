"""
core/channels.py

How a vendor gets told something. One Protocol, one adapter per medium.

Today there is exactly one adapter (email, via Resend). The indirection earns
its keep for two reasons:

  - **SMS is the next channel, not a rewrite.** Trades read texts and ignore
    inboxes. Adding Twilio means one class here plus a `preferred_channel` on
    `Vendor` — the negotiation graph, its prompts, and its guards do not change,
    because the message body and the chat link are identical either way. The
    channel is only how the vendor learns the link exists.
  - **Blocking sends had to be wrapped somewhere.** `core/email.py` is sync
    `def` calling Resend over HTTP, and the negotiation nodes are async. One
    blocking send per dispatch was tolerable; one on every conversation turn
    would stall the event loop. `asyncio.to_thread` is applied here, once,
    instead of at every call site.

Sends are fire-and-forget by design: a notification failure must never roll back
the negotiation that triggered it. Every adapter logs and swallows.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Protocol

from app.core.email import send_negotiation_message_email, send_job_offer_email

logger = logging.getLogger(__name__)


class NotifyChannel(Protocol):
    """One way of reaching a vendor. Mirrors the TaskScheduler Protocol style."""

    name: str

    async def send_job_offer(
        self,
        *,
        to_email: str | None,
        to_phone: str | None,
        vendor_name: str,
        ticket_title: str,
        ticket_summary: str,
        chat_url: str,
    ) -> None: ...

    async def send_message(
        self,
        *,
        to_email: str | None,
        to_phone: str | None,
        vendor_name: str,
        ticket_title: str,
        body: str,
        chat_url: str,
    ) -> None: ...


class EmailChannel:
    """Resend-backed. The only channel wired today."""

    name = "email"

    async def send_job_offer(
        self,
        *,
        to_email: str | None,
        to_phone: str | None,
        vendor_name: str,
        ticket_title: str,
        ticket_summary: str,
        chat_url: str,
    ) -> None:
        if not to_email:
            logger.warning("EmailChannel: no address for vendor %s", vendor_name)
            return
        await asyncio.to_thread(
            send_job_offer_email,
            to_email=to_email,
            vendor_name=vendor_name,
            ticket_title=ticket_title,
            ticket_summary=ticket_summary,
            chat_url=chat_url,
        )

    async def send_message(
        self,
        *,
        to_email: str | None,
        to_phone: str | None,
        vendor_name: str,
        ticket_title: str,
        body: str,
        chat_url: str,
    ) -> None:
        if not to_email:
            logger.warning("EmailChannel: no address for vendor %s", vendor_name)
            return
        await asyncio.to_thread(
            send_negotiation_message_email,
            to_email=to_email,
            vendor_name=vendor_name,
            ticket_title=ticket_title,
            body=body,
            chat_url=chat_url,
        )


_DEFAULT_CHANNEL = EmailChannel()


def channel_for_vendor(vendor) -> NotifyChannel:
    """
    Pick the channel for a vendor.

    Deliberately trivial today — it exists so the SMS switch lands in one place
    rather than being threaded through every node that sends something.
    """
    return _DEFAULT_CHANNEL
