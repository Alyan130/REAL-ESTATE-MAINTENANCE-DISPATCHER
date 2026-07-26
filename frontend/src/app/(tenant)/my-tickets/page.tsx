"use client";

import { motion } from "motion/react";
import { ClipboardList, Plus } from "lucide-react";
import Link from "next/link";

import { TenantStatusBadge } from "@/components/tickets/status-badge";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { FadeIn, StaggerItem, StaggerList } from "@/components/ui/motion-list";
import { PageHeader } from "@/components/ui/page-header";
import { RowsSkeleton } from "@/components/ui/skeleton";
import { listTickets } from "@/lib/api/tickets";
import { formatDate } from "@/lib/format";
import { isTransient } from "@/lib/status";
import { useAsync, usePolling } from "@/lib/use-async";

export default function MyTicketsPage() {
  const tickets = useAsync(() => listTickets(), []);
  const list = tickets.data ?? [];

  const settling = list.some((ticket) => isTransient(ticket.status));
  usePolling(settling, () => void tickets.reload({ silent: true }), {
    intervalMs: 4000,
    maxTicks: 15,
  });

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="My reports"
        description="Everything you've reported, and where each one has got to."
        action={
          <Link href="/my-tickets/new">
            <Button icon={<Plus size={16} />}>Report an issue</Button>
          </Link>
        }
      />

      {tickets.error ? (
        <Alert tone="danger">
          {tickets.error}{" "}
          <button
            type="button"
            className="font-semibold underline cursor-pointer"
            onClick={() => void tickets.reload()}
          >
            Try again
          </button>
        </Alert>
      ) : null}

      {tickets.loading && list.length === 0 ? <RowsSkeleton rows={3} /> : null}

      {!tickets.loading && list.length === 0 ? (
        <FadeIn>
          <EmptyState
            icon={<ClipboardList size={22} />}
            title="Nothing reported yet"
            description="Something broken? Report it with a photo and we'll take it from there — you'll be able to follow the progress right here."
            action={
              <Link href="/my-tickets/new">
                <Button icon={<Plus size={16} />}>Report an issue</Button>
              </Link>
            }
          />
        </FadeIn>
      ) : null}

      {list.length > 0 ? (
        <StaggerList>
          {list.map((ticket) => (
            <StaggerItem key={ticket.id}>
              <motion.div
                whileHover={{ y: -2, boxShadow: "0 6px 20px rgba(0,0,0,0.08)" }}
                transition={{ duration: 0.2, ease: "easeOut" }}
                className="rounded-2xl border border-line-soft bg-surface shadow-card hover:border-line transition-colors"
              >
                <Link
                  href={`/my-tickets/${ticket.id}`}
                  className="flex flex-wrap items-center justify-between gap-3 px-5 py-4"
                >
                  <div className="min-w-0">
                    <p className="font-bold text-ink-strong text-base">{ticket.title}</p>
                    <p className="mt-1 text-xs text-muted font-medium">
                      Submitted {formatDate(ticket.created_at)}
                    </p>
                  </div>
                  <TenantStatusBadge status={ticket.status} />
                </Link>
              </motion.div>
            </StaggerItem>
          ))}
        </StaggerList>
      ) : null}
    </div>
  );
}
