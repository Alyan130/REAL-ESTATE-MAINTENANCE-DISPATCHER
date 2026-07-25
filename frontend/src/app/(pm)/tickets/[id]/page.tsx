"use client";

import {
  ArrowLeft,
  Ban,
  Check,
  DoorOpen,
  Image as ImageIcon,
  Sparkles,
  Zap,
} from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";

import { PhotoGrid } from "@/components/tickets/photo-grid";
import {
  CategoryBadge,
  PriorityBadge,
  StatusBadge,
} from "@/components/tickets/status-badge";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardBody, CardHeader } from "@/components/ui/card";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { FadeIn } from "@/components/ui/motion-list";
import { DetailSkeleton } from "@/components/ui/skeleton";
import { getProperty } from "@/lib/api/properties";
import { getTenant } from "@/lib/api/tenants";
import {
  approveTicket,
  getTicket,
  rejectTicket,
  updateTicketStatus,
} from "@/lib/api/tickets";
import { errorMessage } from "@/lib/errors";
import { formatDateTime } from "@/lib/format";
import { ALL_STATUSES, STATUS_EXPLANATIONS, statusLabel } from "@/lib/status";
import type { TicketStatus } from "@/lib/types";
import { useAsync, usePolling } from "@/lib/use-async";
import { toast } from "@/stores/toast-store";

export default function TicketDetailPage() {
  const params = useParams<{ id: string }>();
  const ticketId = params.id;

  const resource = useAsync(async () => {
    const ticket = await getTicket(ticketId);
    // Both are supporting detail: a deactivated tenant 404s, and that shouldn't
    // take the whole screen down.
    const [property, tenant] = await Promise.all([
      getProperty(ticket.property_id).catch(() => null),
      getTenant(ticket.tenant_id).catch(() => null),
    ]);
    return { ticket, property, tenant };
  }, [ticketId]);

  const [confirmingReject, setConfirmingReject] = useState(false);
  const [approving, setApproving] = useState(false);
  const [rejecting, setRejecting] = useState(false);
  const [overrideStatus, setOverrideStatus] = useState<TicketStatus | "">("");
  const [overriding, setOverriding] = useState(false);
  const [showAdvanced, setShowAdvanced] = useState(false);

  const ticket = resource.data?.ticket;

  // Approval hands off to a background task and answers immediately with
  // DISPATCHING. The settled result (DISPATCHED or NEEDS_ATTENTION) only shows up
  // if we go and look for it.
  usePolling(
    ticket?.status === "DISPATCHING",
    () => void resource.reload({ silent: true }),
    { intervalMs: 3000, maxTicks: 20 },
  );

  const handleApprove = async () => {
    setApproving(true);
    try {
      await approveTicket(ticketId);
      toast.success("Approved. Finding a vendor now.");
    } catch (error) {
      toast.error(errorMessage(error));
    } finally {
      setApproving(false);
      // Reload either way: on a 409 the ticket already moved on, and the screen
      // should show where it actually is.
      await resource.reload({ silent: true });
    }
  };

  const handleReject = async () => {
    setRejecting(true);
    try {
      await rejectTicket(ticketId);
      toast.success("Ticket rejected and cancelled.");
      setConfirmingReject(false);
    } catch (error) {
      toast.error(errorMessage(error));
    } finally {
      setRejecting(false);
      await resource.reload({ silent: true });
    }
  };

  const handleOverride = async () => {
    if (!overrideStatus) return;
    setOverriding(true);
    try {
      await updateTicketStatus(ticketId, overrideStatus);
      toast.success(`Status set to ${statusLabel(overrideStatus)}.`);
      setOverrideStatus("");
    } catch (error) {
      toast.error(errorMessage(error));
    } finally {
      setOverriding(false);
      await resource.reload({ silent: true });
    }
  };

  if (resource.loading && !resource.data) {
    return <DetailSkeleton />;
  }

  if (resource.error && !ticket) {
    return (
      <div className="flex flex-col gap-4">
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

  const { property, tenant } = resource.data!;
  const awaitingDecision = ticket.status === "PENDING_APPROVAL";
  const isEmergency = ticket.priority === "P1";
  const explanation = STATUS_EXPLANATIONS[ticket.status];

  return (
    <div className="flex flex-col gap-6">
      <BackLink />

      <FadeIn>
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="min-w-0">
            <h1 className="text-[2.25rem] leading-tight font-bold">{ticket.title}</h1>
            <p className="mt-1 text-technical text-muted">
              {property?.name ?? "Unknown property"}
              {tenant?.unit_number ? ` · Unit ${tenant.unit_number}` : ""}
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            {ticket.priority ? <PriorityBadge priority={ticket.priority} /> : null}
            {ticket.category ? <CategoryBadge category={ticket.category} /> : null}
            <StatusBadge status={ticket.status} />
          </div>
        </div>
      </FadeIn>

      {explanation ? (
        <Alert
          tone={
            ticket.status === "NEEDS_ATTENTION" || ticket.status === "ERROR"
              ? "danger"
              : ticket.status === "PENDING_APPROVAL"
                ? "warn"
                : "info"
          }
        >
          {explanation}
          {ticket.status === "DISPATCHING" ? (
            <button
              type="button"
              className="ml-1 font-semibold underline"
              onClick={() => void resource.reload({ silent: true })}
            >
              Check now
            </button>
          ) : null}
        </Alert>
      ) : null}

      <div className="grid gap-6 lg:grid-cols-[minmax(0,1.6fr)_minmax(0,1fr)]">
        {/* ── Main column ── */}
        <div className="flex flex-col gap-6">
          <Card>
            <CardHeader title="What the tenant reported" />
            <CardBody className="flex flex-col gap-4">
              {ticket.description ? (
                <p className="whitespace-pre-wrap text-ink">{ticket.description}</p>
              ) : (
                <p className="text-muted italic">
                  No description was provided with this report.
                </p>
              )}

              <div
                className={`flex items-start gap-3 rounded-card border px-4 py-3 ${
                  ticket.permission_to_enter
                    ? "border-success/30 bg-success-soft"
                    : "border-warn/30 bg-warn-soft"
                }`}
              >
                <DoorOpen
                  size={18}
                  className={`mt-0.5 shrink-0 ${
                    ticket.permission_to_enter ? "text-success" : "text-warn"
                  }`}
                />
                <div className="text-sm">
                  <p className="font-semibold text-ink">
                    {ticket.permission_to_enter
                      ? "Vendor may enter when the tenant is out"
                      : "No permission to enter"}
                  </p>
                  <p className="text-muted">
                    {ticket.permission_to_enter
                      ? "Scheduling doesn't depend on the tenant being home."
                      : "A vendor cannot enter unless the tenant is present — the visit has to be scheduled around them."}
                  </p>
                </div>
              </div>
            </CardBody>
          </Card>

          <Card>
            <CardHeader
              title="Photos"
              icon={<ImageIcon size={18} />}
              description={
                ticket.media_urls?.length
                  ? `${ticket.media_urls.length} attached`
                  : undefined
              }
            />
            <CardBody>
              {ticket.media_urls?.length ? (
                <PhotoGrid urls={ticket.media_urls} context={ticket.title} />
              ) : ticket.status === "PENDING_UPLOAD" ? (
                <p className="text-sm text-muted">Photos are still uploading.</p>
              ) : (
                <p className="text-sm text-muted">No photos were attached.</p>
              )}
            </CardBody>
          </Card>
        </div>

        {/* ── Side column ── */}
        <div className="flex flex-col gap-6">
          <Card>
            <CardHeader title="AI triage" icon={<Sparkles size={18} />} />
            <CardBody className="flex flex-col gap-3">
              {ticket.ai_summary ? (
                <p className="text-ink">{ticket.ai_summary}</p>
              ) : (
                <p className="text-sm text-muted italic">
                  {ticket.status === "PENDING_UPLOAD"
                    ? "Classification runs once the photos finish uploading."
                    : "This ticket hasn't been classified."}
                </p>
              )}
              <dl className="grid grid-cols-2 gap-3 text-sm">
                <div>
                  <dt className="text-muted">Priority</dt>
                  <dd className="mt-1">
                    {ticket.priority ? (
                      <PriorityBadge priority={ticket.priority} />
                    ) : (
                      <span className="text-faint">—</span>
                    )}
                  </dd>
                </div>
                <div>
                  <dt className="text-muted">Category</dt>
                  <dd className="mt-1">
                    {ticket.category ? (
                      <CategoryBadge category={ticket.category} />
                    ) : (
                      <span className="text-faint">—</span>
                    )}
                  </dd>
                </div>
              </dl>
            </CardBody>
          </Card>

          <Card>
            <CardHeader title="Your decision" />
            <CardBody className="flex flex-col gap-3">
              {awaitingDecision ? (
                <>
                  <p className="text-sm text-muted">
                    Approving hands off to vendor selection immediately. Rejecting
                    cancels the ticket for good.
                  </p>
                  <div className="flex flex-wrap gap-2">
                    <Button
                      icon={<Check size={16} />}
                      loading={approving}
                      disabled={rejecting}
                      onClick={() => void handleApprove()}
                    >
                      Approve and dispatch
                    </Button>
                    <Button
                      variant="danger"
                      icon={<Ban size={16} />}
                      disabled={approving}
                      onClick={() => setConfirmingReject(true)}
                    >
                      Reject
                    </Button>
                  </div>
                </>
              ) : isEmergency ? (
                <div className="flex items-start gap-3">
                  <Zap size={18} className="mt-0.5 shrink-0 text-danger" />
                  <p className="text-sm text-muted">
                    P1 emergencies dispatch automatically during intake — they never
                    wait on approval. There is nothing for you to approve here.
                  </p>
                </div>
              ) : (
                <p className="text-sm text-muted">
                  This ticket isn&apos;t waiting on you. Approve and reject are only
                  available while a ticket sits at{" "}
                  <span className="text-technical">PENDING_APPROVAL</span>.
                </p>
              )}
            </CardBody>
          </Card>

          <Card>
            <CardHeader title="Details" />
            <CardBody>
              <dl className="flex flex-col gap-3 text-sm">
                <Detail label="Reported by">
                  {tenant ? (
                    <>
                      {tenant.name ?? tenant.email}
                      <span className="block text-technical text-muted">
                        {tenant.email}
                      </span>
                    </>
                  ) : (
                    <span className="text-faint">Tenant no longer active</span>
                  )}
                </Detail>
                <Detail label="Property">
                  {property ? (
                    <Link
                      href={`/properties/${property.id}`}
                      className="font-medium text-brand underline"
                    >
                      {property.name}
                    </Link>
                  ) : (
                    <span className="text-faint">—</span>
                  )}
                  {property ? (
                    <span className="block text-muted">{property.address}</span>
                  ) : null}
                </Detail>
                <Detail label="Unit">
                  {tenant?.unit_number ?? <span className="text-faint">—</span>}
                </Detail>
                <Detail label="Created">
                  <span className="text-technical">
                    {formatDateTime(ticket.created_at)}
                  </span>
                </Detail>
                <Detail label="Last updated">
                  <span className="text-technical">
                    {formatDateTime(ticket.updated_at)}
                  </span>
                </Detail>
                <Detail label="Ticket ID">
                  <span className="text-technical break-all">{ticket.id}</span>
                </Detail>
              </dl>
            </CardBody>
          </Card>

          {/* Escape hatch, not a primary control — mainly for unsticking a
              NEEDS_ATTENTION ticket by hand. */}
          <div>
            <button
              type="button"
              onClick={() => setShowAdvanced((open) => !open)}
              className="text-sm font-medium text-muted underline"
            >
              {showAdvanced ? "Hide advanced" : "Advanced: set status manually"}
            </button>

            {showAdvanced ? (
              <Card className="mt-3">
                <CardBody className="flex flex-col gap-3">
                  <p className="text-sm text-muted">
                    Writes the status directly, skipping the AI workflow. Use this to
                    unstick a ticket, not to move one through the normal flow.
                  </p>
                  <select
                    aria-label="New status"
                    className="h-10 rounded-card border border-line bg-surface px-2.5 text-sm"
                    value={overrideStatus}
                    onChange={(event) =>
                      setOverrideStatus(event.target.value as TicketStatus | "")
                    }
                  >
                    <option value="">Choose a status…</option>
                    {ALL_STATUSES.map((status) => (
                      <option key={status} value={status}>
                        {statusLabel(status)}
                      </option>
                    ))}
                  </select>
                  <div>
                    <Button
                      size="sm"
                      variant="secondary"
                      disabled={!overrideStatus}
                      loading={overriding}
                      onClick={() => void handleOverride()}
                    >
                      Apply status
                    </Button>
                  </div>
                </CardBody>
              </Card>
            ) : null}
          </div>
        </div>
      </div>

      <ConfirmDialog
        open={confirmingReject}
        title="Reject this ticket?"
        destructive
        confirmLabel="Reject ticket"
        loading={rejecting}
        onCancel={() => setConfirmingReject(false)}
        onConfirm={() => void handleReject()}
        body={
          <>
            <p>
              The ticket is cancelled immediately and no vendor is contacted. This
              can&apos;t be undone — the tenant would have to report the issue again.
            </p>
            <p className="mt-3 font-semibold text-ink">{ticket.title}</p>
          </>
        }
      />
    </div>
  );
}

function BackLink() {
  return (
    <Link
      href="/dashboard"
      className="inline-flex items-center gap-1.5 text-sm font-medium text-muted hover:text-ink"
    >
      <ArrowLeft size={15} />
      All tickets
    </Link>
  );
}

function Detail({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <dt className="text-muted">{label}</dt>
      <dd className="mt-0.5 text-ink">{children}</dd>
    </div>
  );
}
