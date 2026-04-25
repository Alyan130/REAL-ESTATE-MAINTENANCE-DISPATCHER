"""
api/routes/auth.py

Authentication routes.
"""
from __future__ import annotations

from typing import Annotated

import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from core.security import create_token, decode_token, hash_password, verify_password
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


class AcceptInviteRequest(BaseModel):
    token: str
    password: str
    confirm_password: str


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


@router.post("/accept-invite", response_model=TokenResponse)
def accept_invite(body: AcceptInviteRequest, db: DbDep) -> TokenResponse:
    """
    Accept an invite token by setting an initial password.

    Returns a login JWT on success.

    - 400 for invalid input or invalid token type.
    - 404 if the user no longer exists.
    - 410 if the invite token is expired or superseded.
    """
    try:
        if body.password != body.confirm_password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Passwords do not match.",
            )

        try:
            payload = decode_token(body.token)
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_410_GONE,
                detail="Invite token has expired.",
            )
        except jwt.PyJWTError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid invite token.",
            )

        if payload.get("type") != "invite":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid token type.",
            )

        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid token payload.",
            )

        user: User | None = db.get(User, user_id)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found.",
            )

        if user.invite_status != "pending":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invite already accepted.",
            )

        token_role = payload.get("role")
        if token_role and token_role != user.role:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid invite token.",
            )

        token_iat_raw = payload.get("iat")
        token_iat: int | None = None
        if token_iat_raw is not None:
            try:
                token_iat = int(token_iat_raw)
            except (TypeError, ValueError):
                token_iat = None

        if (
            user.last_invite_iat is not None
            and token_iat is not None
            and token_iat < user.last_invite_iat
        ):
            raise HTTPException(
                status_code=status.HTTP_410_GONE,
                detail="Invite token has been superseded.",
            )

        user.password_hash = hash_password(body.password)
        user.invite_status = "approved"
        user.last_invite_iat = None
        db.commit()
        db.refresh(user)

        login_token = create_token(
            user_id=user.id,
            role=user.role,
            token_type="login",
        )
        return TokenResponse(access_token=login_token)
    except HTTPException:
        raise
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to accept invite.",
        )
