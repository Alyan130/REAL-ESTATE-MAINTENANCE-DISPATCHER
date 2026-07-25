"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { RowsSkeleton } from "@/components/ui/skeleton";
import { homePathForRole, useAuthStore } from "@/stores/auth-store";

/** Entry point: send the visitor to their role's home, or to login. */
export default function RootPage() {
  const router = useRouter();
  const hydrated = useAuthStore((state) => state.hydrated);
  const token = useAuthStore((state) => state.token);
  const role = useAuthStore((state) => state.role);

  useEffect(() => {
    if (!hydrated) return;
    router.replace(token && role ? homePathForRole(role) : "/login");
  }, [hydrated, token, role, router]);

  return (
    <div className="mx-auto w-full max-w-[1280px] px-6 py-10">
      <RowsSkeleton rows={2} />
    </div>
  );
}
