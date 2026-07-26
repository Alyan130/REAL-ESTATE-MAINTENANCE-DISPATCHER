"""
app/repositories/__init__.py

Data access. Repositories hold queries and staging only — the calling service
owns the transaction.
"""
from app.repositories.base import BaseRepository
from app.repositories.property_repo import PropertyRepository
from app.repositories.tenant_repo import TenantRepository
from app.repositories.ticket_repo import TicketRepository
from app.repositories.user_repo import UserRepository
from app.repositories.vendor_repo import VendorRepository

__all__ = [
    "BaseRepository",
    "PropertyRepository",
    "TenantRepository",
    "TicketRepository",
    "UserRepository",
    "VendorRepository",
]
