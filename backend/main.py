"""
main.py — FastAPI application entry point.
"""
from fastapi import FastAPI

from api.routes import auth

app = FastAPI(
    title="Real Estate Maintenance Dispatcher",
    version="1.0.0",
)

# ─── Routers ──────────────────────────────────────────────────────────────────
app.include_router(auth.router)
