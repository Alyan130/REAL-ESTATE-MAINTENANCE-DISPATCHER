"use client";

import { Building2, HardHat, LayoutDashboard, Users } from "lucide-react";
import type { ReactNode } from "react";

import { AppShell, type NavItem } from "@/components/layout/app-shell";
import { AuthGuard } from "@/components/layout/auth-guard";
import type { Role } from "@/lib/types";

const PM_ONLY: Role[] = ["pm"];

const PM_NAV: NavItem[] = [
  { href: "/dashboard", label: "Tickets", icon: <LayoutDashboard size={18} /> },
  {
    href: "/properties",
    label: "Properties",
    icon: <Building2 size={18} />,
    matchPrefix: true,
  },
  { href: "/tenants", label: "Tenants", icon: <Users size={18} /> },
  { href: "/vendors", label: "Vendors", icon: <HardHat size={18} /> },
];

export default function PropertyManagerLayout({
  children,
}: {
  children: ReactNode;
}) {
  return (
    <AuthGuard allow={PM_ONLY}>
      <AppShell nav={PM_NAV} roleLabel="Property manager">
        {children}
      </AppShell>
    </AuthGuard>
  );
}
