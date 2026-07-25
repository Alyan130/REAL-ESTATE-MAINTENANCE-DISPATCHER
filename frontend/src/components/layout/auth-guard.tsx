"use client";

import { useRouter } from "next/navigation";
import type { ReactNode } from "react";
import { useEffect } from "react";

import { RowsSkeleton } from "@/components/ui/skeleton";
import { setUnauthorizedHandler } from "@/lib/api-client";
import { isTokenExpired } from "@/lib/jwt";
import type { Role } from "@/lib/types";
import { homePathForRole, useAuthStore } from "@/stores/auth-store";

interface AuthGuardProps {
  allow: Role[];
  children: ReactNode;
}

/**
 * Client-side gate. The backend authorises every request independently — this
 * only keeps a signed-out or wrong-role user from staring at a screen that will
 * only ever return 401/403.
 */
export function AuthGuard({ allow, children }: AuthGuardProps) {
  const router = useRouter();
  const token = useAuthStore((state) => state.token);
  const role = useAuthStore((state) => state.role);
  const hydrated = useAuthStore((state) => state.hydrated);
  const signOut = useAuthStore((state) => state.signOut);

  const allowed = allow.join(",");

  // A 401 from any request means the session died mid-use; bounce to login once.
  useEffect(() => {
    setUnauthorizedHandler(() => {
      signOut();
      router.replace("/login?reason=expired");
    });
    return () => setUnauthorizedHandler(null);
  }, [router, signOut]);

  useEffect(() => {
    if (!hydrated) return;

    if (!token || !role || isTokenExpired(token)) {
      signOut();
      router.replace("/login");
      return;
    }

    if (!allowed.split(",").includes(role)) {
      router.replace(homePathForRole(role));
    }
  }, [hydrated, token, role, allowed, router, signOut]);

  const permitted = Boolean(token && role && allowed.split(",").includes(role));

  if (!hydrated || !permitted) {
    return (
      <div className="mx-auto w-full max-w-[1280px] px-6 py-10">
        <RowsSkeleton rows={3} />
      </div>
    );
  }

  return <>{children}</>;
}
