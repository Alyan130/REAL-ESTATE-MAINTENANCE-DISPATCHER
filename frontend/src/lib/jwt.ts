import type { Role } from "@/lib/types";

/**
 * Claims the backend puts on a login token
 * (backend/app/core/security.py :: create_token).
 * There is no /auth/me endpoint, so the role has to be read off the token itself.
 */
export interface TokenClaims {
  sub: string;
  role: Role;
  type: "login" | "invite" | "reset";
  exp: number;
  iat: number;
}

const VALID_ROLES: readonly string[] = ["pm", "tenant", "vendor"];

/**
 * Decode a JWT payload without verifying it.
 *
 * Verification is the backend's job — every request is authorised server-side.
 * This only reads the role so the UI knows which shell to render; a tampered
 * token buys nothing because the API still rejects it.
 */
export function decodeToken(token: string): TokenClaims | null {
  try {
    const payload = token.split(".")[1];
    if (!payload) return null;

    const base64 = payload.replace(/-/g, "+").replace(/_/g, "/");
    const padded = base64.padEnd(base64.length + ((4 - (base64.length % 4)) % 4), "=");
    const json = JSON.parse(
      decodeURIComponent(
        atob(padded)
          .split("")
          .map((char) => `%${`00${char.charCodeAt(0).toString(16)}`.slice(-2)}`)
          .join(""),
      ),
    ) as Partial<TokenClaims>;

    if (typeof json.sub !== "string" || typeof json.role !== "string") return null;
    if (!VALID_ROLES.includes(json.role)) return null;

    return json as TokenClaims;
  } catch {
    return null;
  }
}

/** True when the token is absent, unparseable, or past its `exp`. */
export function isTokenExpired(token: string): boolean {
  const claims = decodeToken(token);
  if (!claims?.exp) return true;
  return claims.exp * 1000 <= Date.now();
}
