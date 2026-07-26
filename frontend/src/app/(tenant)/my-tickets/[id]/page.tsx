"use client";

import { ArrowLeft, DoorOpen } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";

import { PhotoGrid } from "@/components/tickets/photo-grid";
import { TenantStatusBadge } from "@/components/tickets/status-badge";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardBody, CardHeader } from "@/components/ui/card";
import { FadeIn } from "@/components/ui/motion-list";
import { DetailSkeleton } from "@/components/ui/skeleton";
import { getTicket } from "@/lib/api/tickets";
import { formatDateTime } from "@/lib/format";
import { isTransient, tenantStatusLabel } from "@/lib/status";
import { useAsync, usePolling } from "@/lib/use-async";

export default function TenantTicketDetailPage() {
  const params = useParams<{ id: string }>();
  const ticketId = params.id;

  const resource = useAsync(() => getTicket(ticketId), [ticketId]);
  const ticket = resource.data;

  usePolling(
    Boolean(ticket && isTransient(ticket.status)),
    () => void resource.reload({ silent: true }),
    { intervalMs: 4000, maxTicks: 15 },
  );

  if (resource.loading && !ticket) {
    return <DetailSkeleton />;
  }

  if (resource.error && !ticket) {
    return (
      <div className="mx-auto flex w-full max-w-2xl flex-col gap-4">
        <BackLink />
        <Alert tone="danger">{resource.error}</Alert>
        <div>
          <Button variant="secondary" onClick={() => void resource.reload()}>
            Try again
          </Button>
        </div>
      </div>
    );
  }

  if (!ticket) return null;

  return (
    <div className="mx-auto flex w-full max-w-2xl flex-col gap-6">
      <BackLink />

      <FadeIn>
        <div className="flex flex-wrap items-start justify-between gap-3">
          <h1 className="text-[2rem] sm:text-[2.25rem] leading-tight font-bold text-ink-strong">
            {ticket.title}
          </h1>
          <TenantStatusBadge status={ticket.status} />
        </div>
      </FadeIn>

      <Card>
        <CardHeader title="Where this is up to" />
        <CardBody className="flex flex-col gap-3">
          <p className="text-sm font-medium text-ink leading-relaxed">
            {tenantStatusLabel(ticket.status)}
          </p>
          {ticket.status === "PENDING_UPLOAD" ? (
            <p className="text-xs text-muted">
              Your photos are still uploading. This page updates on its own.
            </p>
          ) : null}
          <dl className="grid grid-cols-1 gap-3 text-xs sm:grid-cols-2 pt-1 border-t border-line-soft/80">
            <div>
              <dt className="text-muted font-medium">Submitted</dt>
              <dd className="text-technical text-ink mt-0.5">
                {formatDateTime(ticket.created_at)}
              </dd>
            </div>
            <div>
              <dt className="text-muted font-medium">Last updated</dt>
              <dd className="text-technical text-ink mt-0.5">
                {formatDateTime(ticket.updated_at)}
              </dd>
            </div>
          </dl>
        </CardBody>
      </Card>

      <Card>
        <CardHeader title="What you reported" />
        <CardBody className="flex flex-col gap-4">
          {ticket.description ? (
            <p className="whitespace-pre-wrap text-sm text-ink leading-relaxed">
              {ticket.description}
            </p>
          ) : (
            <p className="text-xs text-muted italic">You didn&apos;t add any extra detail.</p>
          )}

          <div className="flex items-start gap-3 rounded-xl border border-line-soft bg-sunken p-4 text-xs">
            <DoorOpen size={18} className="mt-0.5 shrink-0 text-muted" />
            <p className="text-ink font-medium leading-relaxed">
              {ticket.permission_to_enter
                ? "You said a contractor may enter while you're out."
                : "You said a contractor may not enter unless you're home."}
            </p>
          </div>

          {ticket.media_urls?.length ? (
            <PhotoGrid urls={ticket.media_urls} context={ticket.title} />
          ) : null}
        </CardBody>
      </Card>
    </div>
  );
}

function BackLink() {
  return (
    <Link
      href="/my-tickets"
      className="inline-flex items-center gap-1.5 text-xs font-semibold text-muted hover:text-ink transition-colors"
    >
      <ArrowLeft size={14} />
      My reports
    </Link>
  );
}
