"""
app/middleware.py

Middleware registration, kept out of the application factory so main.py stays
a wiring file.
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings


def register_middleware(app: FastAPI) -> None:
    """
    Attach CORS.

    The frontend runs on its own origin and authenticates with a Bearer header,
    so the browser preflights every request. Origins are allow-listed from
    settings — never "*", since that would let any site call the API with a
    user's token.
    """
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )
