import { AxiosError } from "axios";

/**
 * Stable error codes from the API (backend/app/exceptions.py).
 *
 * Branching on these instead of on message text means copy changes on either
 * side can't silently break a UI branch.
 */
export type ApiErrorCode =
  | "INVALID_CREDENTIALS"
  | "ACCOUNT_PENDING"
  | "ACCOUNT_DISABLED"
  | "NOT_AUTHENTICATED"
  | "PASSWORD_MISMATCH"
  | "INVALID_TOKEN"
  | "INVITE_EXPIRED"
  | "INVITE_SUPERSEDED"
  | "INVITE_ALREADY_ACCEPTED"
  | "DUPLICATE_EMAIL"
  | "TICKET_NOT_AWAITING_APPROVAL"
  | "NOT_FOUND"
  | "FORBIDDEN"
  | "BAD_REQUEST"
  | "CONFLICT"
  | "GONE"
  | "VALIDATION_ERROR"
  | "INTERNAL_ERROR";

/**
 * A normalised, user-safe view of a failed request.
 *
 * Per docs/rules/error-handling.md the user never sees a raw error string or a
 * stack trace, so every API failure is funnelled through here first.
 */
export interface ApiError {
  /** Plain-English message safe to render. */
  message: string;
  /** HTTP status, or 0 when the request never reached the server. */
  status: number;
  /** Machine-readable code, when the response carried one. */
  code: ApiErrorCode | string | null;
  /** True when the network/server was unreachable rather than returning an error. */
  isNetworkError: boolean;
}

const GENERIC_MESSAGE = "Something went wrong. Please try again.";

const STATUS_FALLBACKS: Record<number, string> = {
  400: "That request wasn't valid. Please check the details and try again.",
  401: "Your session has ended. Please sign in again.",
  403: "You don't have permission to do that.",
  404: "We couldn't find what you were looking for.",
  409: "That action is no longer available — this item has already moved on.",
  410: "That link is no longer valid.",
  422: "Some details weren't accepted. Please check the form and try again.",
  500: GENERIC_MESSAGE,
};

interface FastApiValidationIssue {
  loc?: (string | number)[];
  msg?: string;
}

interface ErrorBody {
  /** The API's envelope: {"error": "...", "code": "..."}. */
  error?: string;
  code?: string;
  /** FastAPI's default shape, still possible from anything upstream of the app. */
  detail?: string | FastApiValidationIssue[];
}

function readBody(data: unknown): { message: string | null; code: string | null } {
  if (!data || typeof data !== "object") return { message: null, code: null };

  const body = data as ErrorBody;

  if (typeof body.error === "string" && body.error.trim()) {
    return {
      message: body.error.trim(),
      code: typeof body.code === "string" ? body.code : null,
    };
  }

  // Fallbacks for a bare FastAPI response — e.g. something raised before our
  // handlers are reached.
  if (typeof body.detail === "string" && body.detail.trim()) {
    return { message: body.detail.trim(), code: null };
  }

  if (Array.isArray(body.detail)) {
    const first = body.detail[0];
    if (first?.msg) {
      const field = first.loc?.filter((part) => part !== "body").join(" ");
      return {
        message: field ? `${field}: ${first.msg}` : first.msg,
        code: "VALIDATION_ERROR",
      };
    }
  }

  return { message: null, code: null };
}

export function toApiError(error: unknown): ApiError {
  if (error instanceof AxiosError) {
    if (!error.response) {
      return {
        message:
          "We couldn't reach the server. Check your connection and try again.",
        status: 0,
        code: null,
        isNetworkError: true,
      };
    }

    const status = error.response.status;
    const { message: detail, code } = readBody(error.response.data);

    // 5xx messages are fixed server-side, but never trust one through: a proxy
    // or an upstream error page can still put internals in the body.
    const message =
      status >= 500
        ? GENERIC_MESSAGE
        : detail ?? STATUS_FALLBACKS[status] ?? GENERIC_MESSAGE;

    return { message, status, code, isNetworkError: false };
  }

  return {
    message: GENERIC_MESSAGE,
    status: 0,
    code: null,
    isNetworkError: false,
  };
}

/** Convenience for call sites that only need the sentence. */
export function errorMessage(error: unknown): string {
  return toApiError(error).message;
}
