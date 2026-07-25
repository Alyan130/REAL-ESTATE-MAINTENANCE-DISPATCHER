"""
core/security.py

Cryptographic utilities (bcrypt) and JWT helpers.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
import jwt

from app.config import settings

# ─── Token lifetime map ────────────────────────────────────────────────────────
_TOKEN_LIFETIMES: dict[str, timedelta] = {
    "login": timedelta(days=60),
    "invite": timedelta(hours=48),
    "reset": timedelta(hours=1),
}


# ─── Password helpers ──────────────────────────────────────────────────────────

def hash_password(plain: str) -> str:
    """Return a bcrypt hash of *plain* using the configured work factor."""
    salt = bcrypt.gensalt(rounds=settings.BCRYPT_WORK_FACTOR)
    return bcrypt.hashpw(plain.encode(), salt).decode()


def verify_password(plain: str, hashed: str) -> bool:
    """Return True if *plain* matches the bcrypt *hashed* value."""
    return bcrypt.checkpw(plain.encode(), hashed.encode())


# ─── JWT helpers ───────────────────────────────────────────────────────────────

def create_token(
    user_id: uuid.UUID | str,
    role: str,
    token_type: str,
) -> str:
    """
    Create a signed JWT.

    Payload shape:
        { sub: str(user_id), role: role, type: token_type, exp: <timestamp> }

    token_type → expiry:
        "login"  → 60 days
        "invite" → 48 hours
        "reset"  → 1 hour
    """
    if token_type not in _TOKEN_LIFETIMES:
        raise ValueError(
            f"Unknown token_type '{token_type}'. "
            f"Must be one of: {list(_TOKEN_LIFETIMES)}"
        )

    now = datetime.now(tz=timezone.utc)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "role": role,
        "type": token_type,
        "exp": now + _TOKEN_LIFETIMES[token_type],
        "iat": now,
    }
    return jwt.encode(
        payload,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


def decode_token(token: str) -> dict[str, Any]:
    """
    Decode and verify a JWT.  Raises on bad signature or expiry.

    Returns the decoded payload dict.
    """
    try:
        return jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
    except jwt.ExpiredSignatureError as exc:
        raise jwt.ExpiredSignatureError("Token has expired.") from exc
    except jwt.PyJWTError as exc:
        raise jwt.PyJWTError(f"Invalid token: {exc}") from exc
