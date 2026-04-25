"""
api/deps.py

Re-usable FastAPI dependencies.
"""
from __future__ import annotations

from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from core.security import decode_token
from database import get_db
from models.user import User

_bearer = HTTPBearer()

DbDep = Annotated[Session, Depends(get_db)]
BearerDep = Annotated[HTTPAuthorizationCredentials, Depends(_bearer)]


def get_current_user(
    credentials: BearerDep,
    db: DbDep,
) -> User:
    """
    FastAPI dependency that:
    1. Extracts the Bearer token from the Authorization header.
    2. Decodes and verifies the token (raises 401 on failure).
    3. Loads the user from the database by `sub` claim.
    4. Rejects inactive users with 401.
    5. Returns the full User ORM object.
    """
    _401 = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = decode_token(credentials.credentials)
    except (jwt.ExpiredSignatureError, jwt.PyJWTError):
        raise _401

    user_id: str | None = payload.get("sub")
    if user_id is None:
        raise _401

    user: User | None = db.get(User, user_id)
    if user is None or not user.is_active:
        raise _401

    return user


CurrentUserDep = Annotated[User, Depends(get_current_user)]
