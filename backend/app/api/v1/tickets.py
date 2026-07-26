"""
app/api/v1/tickets.py

Ticket endpoints. Role access is enforced by the dependency on each route; the
lifecycle itself lives in TicketService.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, BackgroundTasks, File, Form, UploadFile, status

from app.dependencies import (
    CurrentUserDep,
    PMUserDep,
    TenantUserDep,
    TicketServiceDep,
)
from app.schemas.tickets import (
    StatusUpdateResponse,
    TicketCreatedResponse,
    TicketResponse,
    UpdateStatusRequest,
)
from app.services.ticket_service import UploadedFile

router = APIRouter(prefix="/tickets", tags=["tickets"])


@router.post("", response_model=TicketCreatedResponse, status_code=status.HTTP_202_ACCEPTED)
def create_ticket(
    background_tasks: BackgroundTasks,
    user: TenantUserDep,
    service: TicketServiceDep,
    title: str = Form(...),
    description: str = Form(None),
    permission_to_enter: bool = Form(False),
    photos: list[UploadFile] = File(default=[]),
) -> TicketCreatedResponse:
    """
    Submit a new maintenance ticket. Tenants only.

    Returns immediately with the ticket ID; photos upload and the AI classifies
    in the background.
    """
    # Read the bytes here, while the request is still alive — the UploadFile
    # streams are closed by the time the background task runs.
    file_contents: list[UploadedFile] = [
        (
            photo.file.read(),
            photo.filename or "photo.jpg",
            photo.content_type or "image/jpeg",
        )
        for photo in photos
    ]

    return service.create(
        user=user,
        title=title,
        description=description,
        permission_to_enter=permission_to_enter,
        files=file_contents,
        schedule=background_tasks.add_task,
    )


@router.get("", response_model=list[TicketResponse])
def list_tickets(
    user: CurrentUserDep,
    service: TicketServiceDep,
    property_id: uuid.UUID | None = None,
    ticket_status: str | None = None,
    category: str | None = None,
) -> list[TicketResponse]:
    """
    List tickets for the caller.

    - **Tenant**: their own tickets only; the filters do not apply.
    - **PM**: every ticket across their properties, with optional filters.
    """
    return service.list_for_user(
        user, property_id=property_id, status=ticket_status, category=category
    )


@router.get("/{ticket_id}", response_model=TicketResponse)
def get_ticket(
    ticket_id: uuid.UUID,
    user: CurrentUserDep,
    service: TicketServiceDep,
) -> TicketResponse:
    """Get one ticket. A tenant must own it; a PM must own its property."""
    return service.get_for_user(ticket_id, user)


@router.patch("/{ticket_id}/status", response_model=StatusUpdateResponse)
def update_ticket_status(
    ticket_id: uuid.UUID,
    body: UpdateStatusRequest,
    pm: PMUserDep,
    service: TicketServiceDep,
) -> StatusUpdateResponse:
    """Manually set a ticket's status. PM only."""
    return service.update_status(ticket_id, pm.id, body.status)


@router.post(
    "/{ticket_id}/approve",
    response_model=StatusUpdateResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def approve_ticket(
    ticket_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    pm: PMUserDep,
    service: TicketServiceDep,
) -> StatusUpdateResponse:
    """
    Approve a ticket and trigger vendor dispatch in the background.

    409 unless the ticket is sitting at PENDING_APPROVAL. P1 tickets auto-dispatch
    during intake and never reach here.
    """
    return service.approve(ticket_id, pm.id, schedule=background_tasks.add_task)


@router.post("/{ticket_id}/reject", response_model=StatusUpdateResponse)
def reject_ticket(
    ticket_id: uuid.UUID,
    pm: PMUserDep,
    service: TicketServiceDep,
) -> StatusUpdateResponse:
    """Reject a ticket. No dispatch; the ticket is cancelled. 409 unless pending."""
    return service.reject(ticket_id, pm.id)
