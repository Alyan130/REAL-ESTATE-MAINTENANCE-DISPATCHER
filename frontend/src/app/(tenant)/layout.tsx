"use client";

import { ClipboardList, CirclePlus } from "lucide-react";
import type { ReactNode } from "react";

import { AppShell, type NavItem } from "@/components/layout/app-shell";
import { AuthGuard } from "@/components/layout/auth-guard";
import type { Role } from "@/lib/types";

const TENANT_ONLY: Role[] = ["tenant"];

const TENANT_NAV: NavItem[] = [
  { href: "/my-tickets", label: "My reports", icon: <ClipboardList size={18} /> },
  {
    href: "/my-tickets/new",
    label: "Report an issue",
    icon: <CirclePlus size={18} />,
  },
];

export default function TenantLayout({ children }: { children: ReactNode }) {
  return (
    <AuthGuard allow={TENANT_ONLY}>
      <AppShell nav={TENANT_NAV} roleLabel="Tenant">
        {children}
      </AppShell>
    </AuthGuard>
  );
}
