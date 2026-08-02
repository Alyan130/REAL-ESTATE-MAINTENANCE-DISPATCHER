"""
app/exceptions.py

Domain exceptions and the handlers that turn them into HTTP responses.

Services raise these instead of `HTTPException`, which keeps the service layer
free of any FastAPI import. Every handler emits the envelope required by
docs/rules/error-handling.md:

    {"error": "Ticket is not awaiting approval.", "code": "TICKET_NOT_AWAITING_APPROVAL"}
"""
from __future__ import annotations

import logging

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)


# ─── Base ────────────────────────────────────────────────────────────────────


class AppError(Exception):
    """Base for every expected failure. `code` is the stable, client-facing key."""

    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    code: str = "INTERNAL_ERROR"
    message: str = "Something went wrong."

    def __init__(self, message: str | None = None) -> None:
        if message is not None:
            self.message = message
        super().__init__(self.message)


# ─── Generic ─────────────────────────────────────────────────────────────────


class NotFoundError(AppError):
    status_code = status.HTTP_404_NOT_FOUND
    code = "NOT_FOUND"
    message = "Not found."

class ForbiddenError(AppError):
    status_code = status.HTTP_403_FORBIDDEN
    code = "FORBIDDEN"
    message = "You do not have access to this resource."


class ValidationError(AppError):
    status_code = status.HTTP_400_BAD_REQUEST
    code = "BAD_REQUEST"
    message = "That request wasn't valid."


# ─── Auth ────────────────────────────────────────────────────────────────────


class InvalidCredentialsError(AppError):
    """Wrong email *or* wrong password — deliberately indistinguishable."""

    status_code = status.HTTP_401_UNAUTHORIZED
    code = "INVALID_CREDENTIALS"
    message = "Invalid email or password."


class AccountPendingError(AppError):
    status_code = status.HTTP_403_FORBIDDEN
    code = "ACCOUNT_PENDING"
    message = "Your account is pending approval."


class AccountDisabledError(AppError):
    status_code = status.HTTP_401_UNAUTHORIZED
    code = "ACCOUNT_DISABLED"
    message = "Account is disabled."


class NotAuthenticatedError(AppError):
    status_code = status.HTTP_401_UNAUTHORIZED
    code = "NOT_AUTHENTICATED"
    message = "Could not validate credentials."


# ─── Invites ─────────────────────────────────────────────────────────────────


class PasswordMismatchError(AppError):
    status_code = status.HTTP_400_BAD_REQUEST
    code = "PASSWORD_MISMATCH"
    message = "Passwords do not match."


class InvalidTokenError(AppError):
    status_code = status.HTTP_400_BAD_REQUEST
    code = "INVALID_TOKEN"
    message = "Invalid invite token."


class InviteExpiredError(AppError):
    status_code = status.HTTP_410_GONE
    code = "INVITE_EXPIRED"
    message = "Invite token has expired."


class InviteSupersededError(AppError):
    """A newer invite was issued, which retires every earlier link."""

    status_code = status.HTTP_410_GONE
    code = "INVITE_SUPERSEDED"
    message = "Invite token has been superseded."


class InviteAlreadyAcceptedError(AppError):
    status_code = status.HTTP_400_BAD_REQUEST
    code = "INVITE_ALREADY_ACCEPTED"
    message = "Invite already accepted."


class DuplicateEmailError(AppError):
    """One account per email address, across all three roles."""

    status_code = status.HTTP_400_BAD_REQUEST
    code = "DUPLICATE_EMAIL"
    message = "A user with this email already exists."


# ─── Tickets ─────────────────────────────────────────────────────────────────


class TicketNotAwaitingApprovalError(AppError):
    status_code = status.HTTP_409_CONFLICT
    code = "TICKET_NOT_AWAITING_APPROVAL"
    message = "Ticket is not awaiting approval."


# ─── Categories ──────────────────────────────────────────────────────────────


class DuplicateCategoryError(AppError):
    status_code = status.HTTP_400_BAD_REQUEST
    code = "DUPLICATE_CATEGORY"
    message = "You already have a category with that name."


class UnknownCategoryError(AppError):
    """A category slug that is not in this PM's vocabulary."""

    status_code = status.HTTP_400_BAD_REQUEST
    code = "UNKNOWN_CATEGORY"
    message = "That category doesn't exist."


class ProtectedCategoryError(AppError):
    """`other` is the intake fallback — the escalation path breaks without it."""

    status_code = status.HTTP_400_BAD_REQUEST
    code = "PROTECTED_CATEGORY"
    message = "The 'Other' category can't be removed."


# ─── Vendor chat / negotiation ───────────────────────────────────────────────


class ChatLinkExpiredError(AppError):
    status_code = status.HTTP_410_GONE
    code = "CHAT_LINK_EXPIRED"
    message = "This link has expired. Ask the property manager to send a new one."


class ChatClosedError(AppError):
    """The job moved on — declined, superseded by another vendor, or timed out."""

    status_code = status.HTTP_410_GONE
    code = "CHAT_CLOSED"
    message = "This job is no longer open."


class ChatReadOnlyError(AppError):
    """The job is settled (approved/completed): history stays readable, replies don't."""

    status_code = status.HTTP_409_CONFLICT
    code = "CHAT_READ_ONLY"
    message = "This conversation is closed to new messages."


class MessageTooFastError(AppError):
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    code = "MESSAGE_TOO_FAST"
    message = "You're sending messages too quickly. Try again in a moment."


class NegotiationNotFoundError(AppError):
    status_code = status.HTTP_404_NOT_FOUND
    code = "NEGOTIATION_NOT_FOUND"
    message = "No active negotiation for this ticket."


class NegotiationNotAwaitingDecisionError(AppError):
    status_code = status.HTTP_409_CONFLICT
    code = "NEGOTIATION_NOT_AWAITING_DECISION"
    message = "This negotiation isn't waiting on your decision."


class CounterLimitReachedError(AppError):
    """One counter round, enforced here as well as in the graph and the column."""

    status_code = status.HTTP_409_CONFLICT
    code = "COUNTER_LIMIT_REACHED"
    message = "You've already sent a counter-offer for this vendor."


# ─── Handlers ────────────────────────────────────────────────────────────────

# Codes for HTTPExceptions raised outside our own hierarchy — FastAPI's own 404
# for an unknown route, HTTPBearer's 403 for a missing header, and so on.
_STATUS_CODES: dict[int, str] = {
    400: "BAD_REQUEST",
    401: "NOT_AUTHENTICATED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    405: "METHOD_NOT_ALLOWED",
    409: "CONFLICT",
    410: "GONE",
    413: "PAYLOAD_TOO_LARGE",
    422: "VALIDATION_ERROR",
    429: "TOO_MANY_REQUESTS",
}

GENERIC_MESSAGE = "Something went wrong. Please try again."


def _envelope(
    status_code: int,
    code: str,
    message: str,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"error": message, "code": code},
        headers=headers,
    )


async def app_error_handler(_: Request, exc: Exception) -> JSONResponse:
    error = exc if isinstance(exc, AppError) else AppError()
    return _envelope(error.status_code, error.code, error.message)


async def http_exception_handler(_: Request, exc: Exception) -> JSONResponse:
    if not isinstance(exc, StarletteHTTPException):
        return _envelope(500, "INTERNAL_ERROR", GENERIC_MESSAGE)

    code = _STATUS_CODES.get(exc.status_code, "INTERNAL_ERROR")
    detail = exc.detail if isinstance(exc.detail, str) and exc.detail else GENERIC_MESSAGE
    # 5xx detail can carry internals; never pass it through.
    message = GENERIC_MESSAGE if exc.status_code >= 500 else detail

    return _envelope(exc.status_code, code, message, getattr(exc, "headers", None))


async def validation_exception_handler(_: Request, exc: Exception) -> JSONResponse:
    """422 from Pydantic. The first issue is enough to tell the user what to fix."""
    message = "Some details weren't accepted."

    if isinstance(exc, RequestValidationError):
        errors = exc.errors()
        if errors:
            first = errors[0]
            field = ".".join(str(part) for part in first.get("loc", ()) if part != "body")
            reason = first.get("msg", "is invalid")
            message = f"{field}: {reason}" if field else reason

    return _envelope(status.HTTP_422_UNPROCESSABLE_ENTITY, "VALIDATION_ERROR", message)


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Last resort. The exception is logged with its traceback; the client gets a
    fixed sentence, never the exception text.
    """
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return _envelope(
        status.HTTP_500_INTERNAL_SERVER_ERROR, "INTERNAL_ERROR", GENERIC_MESSAGE
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
