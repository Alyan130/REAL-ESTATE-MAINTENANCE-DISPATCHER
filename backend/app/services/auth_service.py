"""
app/services/auth_service.py

Sign-in and invite acceptance.
"""
from __future__ import annotations

import uuid

import jwt
from sqlalchemy.orm import Session

from app.core.security import create_token, decode_token, hash_password, verify_password
from app.exceptions import (
    AccountDisabledError,
    AccountPendingError,
    InvalidCredentialsError,
    InvalidTokenError,
    InviteAlreadyAcceptedError,
    InviteExpiredError,
    InviteSupersededError,
    NotFoundError,
    PasswordMismatchError,
)
from app.models.user import User
from app.repositories.user_repo import UserRepository
from app.schemas.auth import AcceptInviteRequest, LoginRequest, TokenResponse
from app.services.base import BaseService


class AuthService(BaseService):
    def __init__(self, db: Session) -> None:
        super().__init__(db)
        self.users = UserRepository(db)

    def login(self, data: LoginRequest) -> TokenResponse:
        """
        Authenticate and issue a login JWT.

        A missing account and a wrong password produce the identical error on
        purpose — telling them apart would confirm which addresses are registered.
        """
        user = self.users.get_by_email(data.email)

        if user is None or not verify_password(data.password, user.password_hash or ""):
            raise InvalidCredentialsError()

        if user.invite_status != "approved":
            raise AccountPendingError()

        if not user.is_active:
            raise AccountDisabledError()

        return TokenResponse(
            access_token=create_token(user_id=user.id, role=user.role, token_type="login")
        )

    def accept_invite(self, data: AcceptInviteRequest) -> TokenResponse:
        """
        Set the initial password from an invite token and sign the user straight in.
        """
        if data.password != data.confirm_password:
            raise PasswordMismatchError()

        payload = self._decode_invite(data.token)
        user = self._load_invited_user(payload)

        self._reject_if_superseded(user, payload)

        user.password_hash = hash_password(data.password)
        user.invite_status = "approved"
        user.last_invite_iat = None
        self._commit()
        self.db.refresh(user)

        return TokenResponse(
            access_token=create_token(user_id=user.id, role=user.role, token_type="login")
        )

    # ─── Internals ───────────────────────────────────────────────────────────

    def _decode_invite(self, token: str) -> dict:
        try:
            payload = decode_token(token)
        except jwt.ExpiredSignatureError:
            raise InviteExpiredError()
        except jwt.PyJWTError:
            raise InvalidTokenError()

        if payload.get("type") != "invite":
            raise InvalidTokenError("Invalid token type.")

        return payload

    def _load_invited_user(self, payload: dict) -> User:
        raw_id = payload.get("sub")
        if not raw_id:
            raise InvalidTokenError("Invalid token payload.")

        try:
            user_id = uuid.UUID(str(raw_id))
        except ValueError:
            raise InvalidTokenError("Invalid token payload.")

        user = self.users.get(user_id)
        if user is None:
            raise NotFoundError("User not found.")

        if user.invite_status != "pending":
            raise InviteAlreadyAcceptedError()

        token_role = payload.get("role")
        if token_role and token_role != user.role:
            raise InvalidTokenError()

        return user

    def _reject_if_superseded(self, user: User, payload: dict) -> None:
        """A resend stamps a newer `iat`, which retires every earlier link."""
        iat_raw = payload.get("iat")
        token_iat: int | None
        try:
            token_iat = int(iat_raw) if iat_raw is not None else None
        except (TypeError, ValueError):
            token_iat = None

        if (
            user.last_invite_iat is not None
            and token_iat is not None
            and token_iat < user.last_invite_iat
        ):
            raise InviteSupersededError()
