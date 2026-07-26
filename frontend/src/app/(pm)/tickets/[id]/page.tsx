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
            <h1 className="text-[2rem] sm:text-[2.25rem] leading-tight font-bold text-ink-strong">
              {ticket.title}
            </h1>
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
              className="ml-1 font-semibold underline cursor-pointer"
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
                <p className="whitespace-pre-wrap text-sm text-ink leading-relaxed">
                  {ticket.description}
                </p>
              ) : (
                <p className="text-xs text-muted italic">
                  No description was provided with this report.
                </p>
              )}

              <div
                className={`flex items-start gap-3 rounded-xl border p-4 ${ticket.permission_to_enter
                    ? "border-success/20 bg-success-soft"
                    : "border-warn/25 bg-warn-soft"
                  }`}
              >
                <DoorOpen
                  size={18}
                  className={`mt-0.5 shrink-0 ${ticket.permission_to_enter ? "text-success" : "text-warn"
                    }`}
                />
                <div className="text-xs">
                  <p className="font-semibold text-ink-strong">
                    {ticket.permission_to_enter
                      ? "Vendor may enter when the tenant is out"
                      : "No permission to enter"}
                  </p>
                  <p className="mt-0.5 text-muted leading-relaxed">
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
                <p className="text-xs text-muted">Photos are still uploading.</p>
              ) : (
                <p className="text-xs text-muted">No photos were attached.</p>
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
                <p className="text-xs font-medium text-ink leading-relaxed">
                  {ticket.ai_summary}
                </p>
              ) : (
                <p className="text-xs text-muted italic">
                  {ticket.status === "PENDING_UPLOAD"
                    ? "Classification runs once the photos finish uploading."
                    : "This ticket hasn't been classified."}
                </p>
              )}
              <dl className="grid grid-cols-2 gap-3 text-xs pt-1 border-t border-line-soft/80">
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
                  <p className="text-xs text-muted leading-relaxed">
                    Approving hands off to vendor selection immediately. Rejecting
                    cancels the ticket for good.
                  </p>
                  <div className="flex flex-wrap gap-2 pt-1">
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
                  <p className="text-xs text-muted leading-relaxed">
                    P1 emergencies dispatch automatically during intake — they never
                    wait on approval. There is nothing for you to approve here.
                  </p>
                </div>
              ) : (
                <p className="text-xs text-muted leading-relaxed">
                  This ticket isn&apos;t waiting on you. Approve and reject are only
                  available while a ticket sits at{" "}
                  <span className="text-technical text-ink">PENDING_APPROVAL</span>.
                </p>
              )}
            </CardBody>
          </Card>

          <Card>
            <CardHeader title="Details" />
            <CardBody>
              <dl className="flex flex-col gap-3 text-xs">
                <Detail label="Reported by">
                  {tenant ? (
                    <>
                      <span className="font-semibold text-ink">{tenant.name ?? tenant.email}</span>
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
                      className="font-semibold text-brand hover:underline"
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

          <div>
            <button
              type="button"
              onClick={() => setShowAdvanced((open) => !open)}
              className="text-xs font-semibold text-muted underline hover:text-ink cursor-pointer"
            >
              {showAdvanced ? "Hide advanced" : "Advanced: set status manually"}
            </button>

            {showAdvanced ? (
              <Card className="mt-3">
                <CardBody className="flex flex-col gap-3">
                  <p className="text-xs text-muted leading-relaxed">
                    Writes the status directly, skipping the AI workflow. Use this to
                    unstick a ticket, not to move one through the normal flow.
                  </p>
                  <select
                    aria-label="New status"
                    className="h-9 rounded-full border border-line-soft bg-surface px-3.5 text-xs font-semibold text-ink cursor-pointer"
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
            <p className="text-xs text-muted">
              The ticket is cancelled immediately and no vendor is contacted. This
              can&apos;t be undone — the tenant would have to report the issue again.
            </p>
            <p className="mt-3 font-bold text-ink-strong text-sm">{ticket.title}</p>
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
      className="inline-flex items-center gap-1.5 text-xs font-semibold text-muted hover:text-ink transition-colors"
    >
      <ArrowLeft size={14} />
      All tickets
    </Link>
  );
}

function Detail({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <dt className="text-muted text-xs font-medium">{label}</dt>
      <dd className="mt-0.5 text-ink text-xs">{children}</dd>
    </div>
  );
}
