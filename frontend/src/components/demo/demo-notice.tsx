"use client";

/**
 * TEMPORARY — see lib/demo/fixtures.ts.
 *
 * Makes it impossible to mistake demo data for real data, and puts the sign-in
 * details on the one screen where they're needed.
 */
import { FlaskConical } from "lucide-react";

import { Button } from "@/components/ui/button";
import { IS_DEMO_MODE } from "@/lib/api-client";
import { DEMO_PASSWORD } from "@/lib/demo/fixtures";

interface DemoAccount {
  label: string;
  email: string;
  detail: string;
}

const ACCOUNTS: DemoAccount[] = [
  {
    label: "Property manager",
    email: "pm@demo.test",
    detail: "3 properties, 8 tickets, 2 awaiting your approval",
  },
  {
    label: "Tenant",
    email: "tenant@demo.test",
    detail: "Priya Raman, Maple Court Unit 4B — 4 reports",
  },
  {
    label: "Vendor",
    email: "vendor@demo.test",
    detail: "Lands on the not-built-yet notice",
  },
];

/** Always-visible marker that the data is fake. */
export function DemoBadge() {
  if (!IS_DEMO_MODE) return null;

  return (
    <div className="pointer-events-none fixed bottom-4 left-4 z-[400]">
      <span className="inline-flex items-center gap-1.5 rounded-full border border-warn/40 bg-warn-soft px-3 py-1 text-xs font-semibold text-warn shadow-card">
        <FlaskConical size={13} />
        Demo data — no backend
      </span>
    </div>
  );
}

/** Credential picker shown on the login screen. */
export function DemoCredentials({
  onPick,
}: {
  onPick: (email: string, password: string) => void;
}) {
  if (!IS_DEMO_MODE) return null;

  return (
    <div className="rounded-card border border-warn/30 bg-warn-soft/60 p-4">
      <p className="label-ui text-ink">
        Demo mode — pick an account
        <span className="ml-1.5 text-xs font-normal text-muted">
          password{" "}
          <span className="text-technical text-ink">{DEMO_PASSWORD}</span>
        </span>
      </p>

      <div className="mt-3 flex flex-col gap-2">
        {ACCOUNTS.map((account) => (
          <button
            key={account.email}
            type="button"
            onClick={() => onPick(account.email, DEMO_PASSWORD)}
            className="rounded-card border border-line-soft bg-surface px-3 py-2 text-left hover:border-brand"
          >
            <span className="block text-sm font-semibold text-ink-strong">
              {account.label}
              <span className="ml-2 text-technical font-normal text-muted">
                {account.email}
              </span>
            </span>
            <span className="block text-xs text-muted">{account.detail}</span>
          </button>
        ))}
      </div>

      <p className="mt-3 text-xs text-muted">
        Try <span className="text-technical">sofia@demo.test</span> for the
        pending-invite error, or{" "}
        <span className="text-technical">disabled@demo.test</span> for a disabled
        account.
      </p>
    </div>
  );
}

/** Link row for exercising the accept-invite screen's error states. */
export function DemoInviteLinks() {
  if (!IS_DEMO_MODE) return null;

  const tokens = [
    ["Working invite", "demo"],
    ["Expired", "expired"],
    ["Superseded", "superseded"],
    ["Already used", "used"],
  ] as const;

  return (
    <div className="mt-6 rounded-card border border-warn/30 bg-warn-soft/60 p-4">
      <p className="label-ui text-ink">Demo mode — invite links</p>
      <div className="mt-2 flex flex-wrap gap-2">
        {tokens.map(([label, token]) => (
          <a key={token} href={`/accept-invite?token=${token}`}>
            <Button size="sm" variant="secondary">
              {label}
            </Button>
          </a>
        ))}
      </div>
    </div>
  );
}
