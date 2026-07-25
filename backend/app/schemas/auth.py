"""
schemas/auth.py

Pydantic models for authentication and invite-acceptance endpoints.
"""
from __future__ import annotations

from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class AcceptInviteRequest(BaseModel):
    token: str
    password: str
    confirm_password: str


class ResendInviteResponse(BaseModel):
    ok: bool = True
