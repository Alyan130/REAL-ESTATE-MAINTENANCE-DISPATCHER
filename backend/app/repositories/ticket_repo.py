"""app/repositories/ticket_repo.py"""
from __future__ import annotations

import uuid

from app.models.ticket import Ticket
from app.repositories.base import BaseRepository


class TicketRepository(BaseRepository[Ticket]):
    model = Ticket

    def list_for_tenant(self, tenant_id: uuid.UUID) -> list[Ticket]:
        return (
            self.db.query(Ticket)
            .filter(Ticket.tenant_id == tenant_id)
            .order_by(Ticket.created_at.desc())
            .all()
        )

    def list_for_properties(
        self,
        property_ids: list[uuid.UUID],
        property_id: uuid.UUID | None = None,
        status: str | None = None,
        category: str | None = None,
    ) -> list[Ticket]:
        """
        Tickets across a PM's properties, newest first.

        `property_ids` is the ownership scope and is always applied; the three
        optional arguments are the user-facing filters.
        """
        if not property_ids:
            return []

        query = self.db.query(Ticket).filter(Ticket.property_id.in_(property_ids))

        if property_id is not None:
            query = query.filter(Ticket.property_id == property_id)
        if status is not None:
            query = query.filter(Ticket.status == status)
        if category is not None:
            query = query.filter(Ticket.category == category)

        return query.order_by(Ticket.created_at.desc()).all()
