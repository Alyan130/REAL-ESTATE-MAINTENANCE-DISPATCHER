import axios from "axios";

import { demoAdapter } from "@/lib/demo/demo-adapter";

/**
 * Single axios instance for the whole app.
 *
 * The bearer token lives in module scope rather than being read from storage on
 * every request, and is pushed here by the auth store. That keeps the dependency
 * one-directional (store -> client) and avoids an import cycle.
 */
export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

/** TEMPORARY — see lib/demo/fixtures.ts. Remove with the demo folder. */
export const IS_DEMO_MODE = process.env.NEXT_PUBLIC_DEMO_MODE === "true";

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: { "Content-Type": "application/json" },
  timeout: 30_000,
});

// Swapping the transport is the only concession the app makes to demo mode.
// Every interceptor, store, and screen below this line runs unchanged.
if (IS_DEMO_MODE) {
  apiClient.defaults.adapter = demoAdapter;
}

let authToken: string | null = null;
let onUnauthorized: (() => void) | null = null;

export function setAuthToken(token: string | null): void {
  authToken = token;
}

/** Registered once by the auth guard so an expired session can bounce to login. */
export function setUnauthorizedHandler(handler: (() => void) | null): void {
  onUnauthorized = handler;
}

/** Endpoints where a 401 is an expected answer, not a dead session. */
const PUBLIC_AUTH_PATHS = ["/auth/login", "/auth/accept-invite"];

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
