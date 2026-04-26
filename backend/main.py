"""
main.py — FastAPI application entry point.
"""
from fastapi import FastAPI

from api.routes import auth, pm

app = FastAPI(
    title="Real Estate Maintenance Dispatcher",
    version="1.0.0",
)

# ─── Routers ──────────────────────────────────────────────────────────────────
app.include_router(auth.router)
app.include_router(pm.router)
