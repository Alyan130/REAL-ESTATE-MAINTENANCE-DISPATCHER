import axios from "axios";

/**
 * Single axios instance for the whole app.
 *
 * The bearer token lives in module scope rather than being read from storage on
 * every request, and is pushed here by the auth store. That keeps the dependency
 * one-directional (store -> client) and avoids an import cycle.
 */
export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: { "Content-Type": "application/json" },
  timeout: 30_000,
});

let authToken: string | null = null;
let onUnauthorized: (() => void) | null = null;

export function setAuthToken(token: string | null): void {
  authToken = token;
}

/** Registered once by the auth guard so an expired session can bounce to login. */
export function setUnauthorizedHandler(handler: (() => void) | null): void {
  onUnauthorized = handler;
}

/**
 * Endpoints where a 401 is an expected answer, not a dead session.
 *
 * `/vendor-chat` is token-gated rather than session-gated, so a PM signed in on
 * the same browser must not be bounced to login by a vendor link going stale.
 * Its own failures are 400/410 rather than 401, so this is belt-and-braces.
 */
const PUBLIC_AUTH_PATHS = ["/auth/login", "/auth/accept-invite", "/vendor-chat"];

apiClient.interceptors.request.use((config) => {
  if (authToken) {
    config.headers.Authorization = `Bearer ${authToken}`;
  }
  return config;
});

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error?.response?.status;
    const url: string = error?.config?.url ?? "";
    const isPublicAuthCall = PUBLIC_AUTH_PATHS.some((path) => url.startsWith(path));

    if (status === 401 && !isPublicAuthCall) {
      onUnauthorized?.();
    }

    return Promise.reject(error);
  },
);
