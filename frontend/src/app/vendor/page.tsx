"use client";

import { HardHat, LogOut, Mail } from "lucide-react";
import { useRouter } from "next/navigation";

import { AuthGuard } from "@/components/layout/auth-guard";
import { Button } from "@/components/ui/button";
import { Card, CardBody } from "@/components/ui/card";
import { FadeIn } from "@/components/ui/motion-list";
import type { Role } from "@/lib/types";
import { useAuthStore } from "@/stores/auth-store";

const VENDOR_ONLY: Role[] = ["vendor"];

export default function VendorPage() {
  const router = useRouter();
  const signOut = useAuthStore((state) => state.signOut);
  const email = useAuthStore((state) => state.email);

  return (
    <AuthGuard allow={VENDOR_ONLY}>
      <div className="flex min-h-[100dvh] items-center justify-center bg-canvas px-6 py-12">
        <FadeIn className="w-full max-w-lg">
          <Card>
            <CardBody className="flex flex-col items-start gap-5 p-8">
              <span className="flex h-12 w-12 items-center justify-center rounded-2xl bg-brand-soft text-brand shadow-xs">
                <HardHat size={22} />
              </span>

              <div>
                <h1 className="text-2xl font-bold text-ink-strong">Your account is set up</h1>
                <p className="mt-2 text-xs text-muted leading-relaxed">
                  The vendor portal — job list, quotes, completion photos, and
                  invoices — isn&apos;t available yet.
                </p>
              </div>

              <div className="flex items-start gap-3 rounded-xl border border-line-soft bg-sunken p-4 text-xs">
                <Mail size={18} className="mt-0.5 shrink-0 text-brand" />
                <p className="text-ink leading-relaxed">
                  Until it ships, job offers reach you by email with the description
                  and photos. Reply to the property manager directly to quote.
                </p>
              </div>

              {email ? (
                <p className="text-technical text-faint text-xs">Signed in as {email}</p>
              ) : null}

              <Button
                variant="secondary"
                icon={<LogOut size={15} />}
                onClick={() => {
                  signOut();
                  router.replace("/login");
                }}
              >
                Sign out
              </Button>
            </CardBody>
          </Card>
        </FadeIn>
      </div>
    </AuthGuard>
  );
}
