"""
app/api/v1/vendor_chat.py

The vendor's negotiation thread. **No auth dependency** — the token IS the
authentication, exactly like accept-invite.

The token lives in the path rather than the query string, so one
`PUBLIC_AUTH_PATHS` entry covers both routes and the token never lands in
axios's query logging.
"""
from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, status

from app.dependencies import NegotiationServiceDep
from app.schemas.negotiation import (
    MessageAcceptedResponse,
    PostMessageRequest,
    VendorChatResponse,
)

router = APIRouter(prefix="/vendor-chat", tags=["vendor-chat"])


@router.get("/{token}", response_model=VendorChatResponse)
def get_chat(token: str, service: NegotiationServiceDep) -> VendorChatResponse:
    """The job, the transcript, and whether this vendor can still reply."""
    return service.get_chat(token)


@router.post(
    "/{token}/messages",
    response_model=MessageAcceptedResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def post_message(
    token: str,
    data: PostMessageRequest,
    background_tasks: BackgroundTasks,
    service: NegotiationServiceDep,
) -> MessageAcceptedResponse:
    """
    Store the vendor's message and wake the agent.

    202, not 201: the message is saved synchronously so it appears on reload,
    but the AI's answer is written by a background task and arrives on a later
    poll.
    """
    return service.post_message(token, data.body, background_tasks.add_task)
