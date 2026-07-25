import { Network } from "lucide-react";
import type { ReactNode } from "react";

import { NetworkPanel } from "@/components/brand/network-panel";

interface AuthLayoutProps {
  title: string;
  subtitle: string;
  children: ReactNode;
}

/** Split-screen: form on the left, topology visual on the right (collapses below md). */
export function AuthLayout({ title, subtitle, children }: AuthLayoutProps) {
  return (
    <div className="grid min-h-[100dvh] grid-cols-1 md:grid-cols-[minmax(0,1fr)_minmax(0,0.85fr)]">
      <div className="flex items-center justify-center px-6 py-12">
        <div className="w-full max-w-md">
          <div className="mb-8 flex items-center gap-2.5">
            <span className="flex h-9 w-9 items-center justify-center rounded-card bg-brand text-white">
              <Network size={18} />
            </span>
            <span className="text-sm font-bold tracking-tight text-ink-strong">
              Maintenance Dispatcher
            </span>
          </div>

          <h1 className="text-[2.25rem] leading-tight font-bold">{title}</h1>
          <p className="mt-2 text-muted">{subtitle}</p>

          <div className="mt-8">{children}</div>
        </div>
      </div>

      <div className="hidden items-center justify-center bg-shell px-10 py-12 md:flex">
        <div className="w-full max-w-md">
          <NetworkPanel />
          <p className="mt-8 max-w-[36ch] text-sm text-white/70">
            Tenant reports are classified, priced, and routed to a vendor
            automatically. You only step in for the approve or reject call.
          </p>
        </div>
      </div>
    </div>
  );
}
