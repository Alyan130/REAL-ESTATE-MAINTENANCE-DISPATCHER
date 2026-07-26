"use client";

import { ArrowLeft, Inbox, MapPin, UserPlus, Users } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";

import { InviteTenantModal } from "@/components/tenants/invite-tenant-modal";
import { TicketRow } from "@/components/tickets/ticket-row";
import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardBody, CardHeader } from "@/components/ui/card";
import { FadeIn, StaggerItem, StaggerList } from "@/components/ui/motion-list";
import { DetailSkeleton } from "@/components/ui/skeleton";
import { getProperty } from "@/lib/api/properties";
import { listTenants } from "@/lib/api/tenants";
import { listTickets } from "@/lib/api/tickets";
import { isTransient } from "@/lib/status";
import { useAsync, usePolling } from "@/lib/use-async";

export default function PropertyDetailPage() {
  const params = useParams<{ id: string }>();
  const propertyId = params.id;
  const [inviting, setInviting] = useState(false);

  const property = useAsync(() => getProperty(propertyId), [propertyId]);
  const tenants = useAsync(() => listTenants(propertyId), [propertyId]);
  const tickets = useAsync(
    () => listTickets({ property_id: propertyId }),
    [propertyId],
  );

  const ticketList = tickets.data ?? [];
  const hasPendingWork = ticketList.some((ticket) => isTransient(ticket.status));
  usePolling(hasPendingWork, () => void tickets.reload({ silent: true }), {
    intervalMs: 5000,
    maxTicks: 24,
  });

  if (property.loading && !property.data) {
    return <DetailSkeleton />;
  }

  if (property.error && !property.data) {
    return (
      <div className="flex flex-col gap-4">
        <BackLink />
        <Alert tone="danger">{property.error}</Alert>
      </div>
    );
  }

  if (!property.data) return null;

  const tenantList = tenants.data ?? [];

  return (
    <div className="flex flex-col gap-6">
      <BackLink />

      <FadeIn>
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <h1 className="text-[2rem] sm:text-[2.25rem] leading-tight font-bold text-ink-strong">
              {property.data.name}
            </h1>
            <p className="mt-1 flex items-center gap-1.5 text-xs text-muted font-medium">
              <MapPin size={14} className="text-brand shrink-0" />
              {property.data.address}
            </p>
          </div>
          <Button icon={<UserPlus size={16} />} onClick={() => setInviting(true)}>
            Invite tenant here
          </Button>
        </div>
      </FadeIn>

      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.4fr)]">
        <Card>
          <CardHeader
            title="Tenants"
            icon={<Users size={18} />}
            description={`${tenantList.length} at this property`}
          />
          <CardBody>
            {tenants.error ? <Alert tone="danger">{tenants.error}</Alert> : null}

            {!tenants.loading && tenantList.length === 0 ? (
              <p className="text-xs text-muted">
                Nobody has been invited to this property yet. A tenant has to exist
                before a ticket can arrive from here.
              </p>
            ) : null}

            <ul className="flex flex-col gap-3">
              {tenantList.map((tenant) => (
                <li
                  key={tenant.id}
                  className="flex flex-wrap items-start justify-between gap-2 border-b border-line-soft/80 pb-3 last:border-0 last:pb-0"
                >
                  <div className="min-w-0">
                    <p className="font-semibold text-xs text-ink-strong">
                      {tenant.name ?? "Unnamed tenant"}
                      {tenant.unit_number ? (
                        <span className="text-muted font-normal"> · Unit {tenant.unit_number}</span>
                      ) : null}
                    </p>
                    <p className="text-xs text-muted mt-0.5">{tenant.email}</p>
                  </div>
                  <Badge
                    tone={tenant.invite_status === "pending" ? "warn" : "success"}
                  >
                    {tenant.invite_status === "pending" ? "Invite pending" : "Active"}
                  </Badge>
                </li>
              ))}
            </ul>
          </CardBody>
        </Card>

        <section className="flex flex-col gap-3">
          <div className="flex items-center gap-2">
            <Inbox size={18} className="text-brand shrink-0" />
            <h2 className="text-base font-bold text-ink-strong">Tickets here</h2>
            <span className="text-technical text-muted text-xs">{ticketList.length}</span>
          </div>

          {tickets.error ? <Alert tone="danger">{tickets.error}</Alert> : null}

          {!tickets.loading && ticketList.length === 0 ? (
            <Card>
              <CardBody>
                <p className="text-xs text-muted">
                  Nothing has been reported at this property.
                </p>
              </CardBody>
            </Card>
          ) : null}

          <StaggerList>
            {ticketList.map((ticket) => (
              <StaggerItem key={ticket.id}>
                <TicketRow ticket={ticket} propertyName={property.data!.name} />
              </StaggerItem>
            ))}
          </StaggerList>
        </section>
      </div>

      <InviteTenantModal
        open={inviting}
        properties={property.data ? [property.data] : []}
        lockedPropertyId={propertyId}
        onClose={() => setInviting(false)}
        onInvited={() => void tenants.reload({ silent: true })}
      />
    </div>
  );
}

function BackLink() {
  return (
    <Link
      href="/properties"
      className="inline-flex items-center gap-1.5 text-xs font-semibold text-muted hover:text-ink transition-colors"
    >
      <ArrowLeft size={14} />
      All properties
    </Link>
  );
}
