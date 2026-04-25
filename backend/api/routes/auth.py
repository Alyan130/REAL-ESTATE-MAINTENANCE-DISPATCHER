"""
api/routes/auth.py

Authentication routes.
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from core.security import create_token, verify_password
from database import get_db
from models.user import User

router = APIRouter(prefix="/auth", tags=["auth"])

DbDep = Annotated[Session, Depends(get_db)]


# ─── Schemas ──────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: DbDep) -> TokenResponse:
    """
    Authenticate a user and return a signed JWT.

    - 401 if email not found or password is wrong.
    - 403 if the user's invite_status is still 'pending'.
    - 200 + JWT on success.
    """
    user: User | None = (
        db.query(User).filter(User.email == body.email).first()
    )

    # Email not found OR password mismatch → same generic 401
    if user is None or not verify_password(body.password, user.password_hash or ""):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    # Account not yet approved
    if user.invite_status != "approved":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account is pending approval.",
        )

    # Inactive account
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is disabled.",
        )

    token = create_token(
        user_id=user.id,
        role=user.role,
        token_type="login",
    )
    return TokenResponse(access_token=token)
