"""
main.py — FastAPI application entry point.
"""
from fastapi import FastAPI

from api.routes import auth, properties, tenants, tickets, vendors

app = FastAPI(
    title="Real Estate Maintenance Dispatcher",
    version="1.0.0",
)

# ─── Routers ──────────────────────────────────────────────────────────────────
app.include_router(auth.router)
app.include_router(properties.router)
app.include_router(tenants.router)
app.include_router(vendors.router)
app.include_router(tickets.router)

