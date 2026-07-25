import { create } from "zustand";
import { createJSONStorage, persist } from "zustand/middleware";

import { setAuthToken } from "@/lib/api-client";
import { decodeToken, isTokenExpired } from "@/lib/jwt";
import type { Role } from "@/lib/types";

interface AuthState {
  token: string | null;
  role: Role | null;
  userId: string | null;
  /** Captured from the login form; the token carries no email claim. */
  email: string | null;
  /** False until persisted state has been read back on the client. */
  hydrated: boolean;

  signIn: (token: string, email?: string) => Role | null;
  signOut: () => void;
  setHydrated: () => void;
}

/**
 * Session state.
 *
 * The token is a bearer JWT held in localStorage: the backend has no cookie or
 * refresh flow, so this is the only place it can live. It is never logged, and
 * the role is read from the token's claims rather than trusted from anywhere else.
 */
export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      token: null,
      role: null,
      userId: null,
      email: null,
      hydrated: false,

      signIn: (token, email) => {
        const claims = decodeToken(token);
        if (!claims) {
          setAuthToken(null);
          set({ token: null, role: null, userId: null, email: null });
          return null;
        }

        setAuthToken(token);
        set({
          token,
          role: claims.role,
          userId: claims.sub,
          email: email ?? null,
        });
        return claims.role;
      },

      signOut: () => {
        setAuthToken(null);
        set({ token: null, role: null, userId: null, email: null });
      },

      setHydrated: () => set({ hydrated: true }),
    }),
    {
      name: "dispatcher-auth",
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({
        token: state.token,
        role: state.role,
        userId: state.userId,
        email: state.email,
      }),
      onRehydrateStorage: () => (state) => {
        // Push the restored token into the axios client, or drop a stale session
        // so the user lands on login instead of watching every request 401.
        if (state?.token && !isTokenExpired(state.token)) {
          setAuthToken(state.token);
        } else if (state) {
          setAuthToken(null);
          state.token = null;
          state.role = null;
          state.userId = null;
          state.email = null;
        }
        state?.setHydrated();
      },
    },
  ),
);

/** Where a role lands after signing in. */
export function homePathForRole(role: Role): string {
  switch (role) {
    case "pm":
      return "/dashboard";
    case "tenant":
      return "/my-tickets";
    case "vendor":
      return "/vendor";
  }
}
