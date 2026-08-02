"""
Tests for the vendor chat token — the feature's main security surface.

The chat page has no authentication of its own: the token *is* the credential.
Everything here is a rejection path, because the only interesting question about
an unauthenticated endpoint is what it refuses.

These use a stub session rather than Postgres. The models use `postgresql.UUID`
and `ARRAY`, so SQLite cannot stand in, and the token branches worth testing all
resolve before any row is fetched. Coverage of the row-dependent branches
(terminal status, inactive vendor) needs a real database — see the plan's note
about `TEST_DATABASE_URL`.
"""
import uuid
from datetime import datetime, timedelta, timezone

import jwt
import pytest

from app.config import settings
from app.core.security import create_token
from app.exceptions import ChatLinkExpiredError, InvalidTokenError, NotFoundError
from app.services.negotiation_service import NegotiationService


class _StubSession:
    """Answers every lookup with None — enough to reach the token branches."""

    def get(self, *_args, **_kwargs):
        return None


@pytest.fixture
def service():
    return NegotiationService(_StubSession())


def _expired_job_token(job_id: uuid.UUID) -> str:
    past = datetime.now(tz=timezone.utc) - timedelta(hours=1)
    return jwt.encode(
        {
            "sub": str(job_id),
            "role": "vendor",
            "type": "job",
            "exp": past,
            "iat": past - timedelta(days=1),
        },
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


def test_login_token_is_rejected(service):
    """
    The type-confusion guard. Without it, any signed JWT reaching this endpoint
    would be treated as a chat credential.
    """
    token = create_token(user_id=uuid.uuid4(), role="pm", token_type="login")
    with pytest.raises(InvalidTokenError):
        service._authorise_chat(token)


def test_invite_token_is_rejected(service):
    token = create_token(user_id=uuid.uuid4(), role="vendor", token_type="invite")
    with pytest.raises(InvalidTokenError):
        service._authorise_chat(token)


def test_reset_token_is_rejected(service):
    token = create_token(user_id=uuid.uuid4(), role="vendor", token_type="reset")
    with pytest.raises(InvalidTokenError):
        service._authorise_chat(token)


def test_garbage_token_is_rejected(service):
    with pytest.raises(InvalidTokenError):
        service._authorise_chat("not-a-jwt")


def test_token_signed_with_another_key_is_rejected(service):
    forged = jwt.encode(
        {
            "sub": str(uuid.uuid4()),
            "role": "vendor",
            "type": "job",
            "exp": datetime.now(tz=timezone.utc) + timedelta(days=1),
        },
        "a-different-secret",
        algorithm="HS256",
    )
    with pytest.raises(InvalidTokenError):
        service._authorise_chat(forged)


def test_expired_token_reports_expiry_not_invalidity(service):
    """A vendor with a stale link deserves 'expired', not 'invalid'."""
    with pytest.raises(ChatLinkExpiredError):
        service._authorise_chat(_expired_job_token(uuid.uuid4()))


def test_job_token_with_wrong_role_is_rejected(service):
    token = jwt.encode(
        {
            "sub": str(uuid.uuid4()),
            "role": "pm",
            "type": "job",
            "exp": datetime.now(tz=timezone.utc) + timedelta(days=1),
        },
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )
    with pytest.raises(InvalidTokenError):
        service._authorise_chat(token)


def test_non_uuid_subject_is_rejected_not_500(service):
    """A bad `sub` must not reach the database and surface as a 500."""
    token = jwt.encode(
        {
            "sub": "definitely-not-a-uuid",
            "role": "vendor",
            "type": "job",
            "exp": datetime.now(tz=timezone.utc) + timedelta(days=1),
        },
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )
    with pytest.raises(InvalidTokenError):
        service._authorise_chat(token)


def test_valid_token_for_a_missing_job_is_a_404(service):
    """Well-formed, correctly signed, but the job is gone."""
    token = create_token(user_id=uuid.uuid4(), role="vendor", token_type="job")
    with pytest.raises(NotFoundError):
        service._authorise_chat(token)


def test_minted_token_carries_the_job_id_as_subject():
    """`sub` is a vendor_jobs.id — that scoping is the whole security model."""
    from app.agentic_AI.tools.negotiation import mint_chat_token

    job_id = uuid.uuid4()
    payload = jwt.decode(
        mint_chat_token(job_id),
        settings.JWT_SECRET_KEY,
        algorithms=[settings.JWT_ALGORITHM],
    )
    assert payload["sub"] == str(job_id)
    assert payload["type"] == "job"
    assert payload["role"] == "vendor"
