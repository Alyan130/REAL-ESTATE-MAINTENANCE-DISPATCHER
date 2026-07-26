"""
app/api/v1/router.py

v1 router aggregation.
"""
from fastapi import APIRouter

from app.api.v1 import auth, properties, tenants, tickets, vendors

router = APIRouter()

router.include_router(auth.router)
router.include_router(properties.router)
router.include_router(tenants.router)
router.include_router(vendors.router)
router.include_router(tickets.router)
