"use client";

import { Building2, Inbox, RefreshCw, SearchX, TriangleAlert } from "lucide-react";
import Link from "next/link";
import { useMemo, useState } from "react";

import {
  EMPTY_FILTERS,
  TicketFilters,
  type TicketFilterValue,
} from "@/components/tickets/ticket-filters";
import { TicketRow } from "@/components/tickets/ticket-row";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { FadeIn, StaggerItem, StaggerList } from "@/components/ui/motion-list";
import { PageHeader } from "@/components/ui/page-header";
import { RowsSkeleton } from "@/components/ui/skeleton";
import { listProperties } from "@/lib/api/properties";
import { listTickets } from "@/lib/api/tickets";
import { isActionRequired, isTransient } from "@/lib/status";
import type { Ticket } from "@/lib/types";
import { useAsync, usePolling } from "@/lib/use-async";

export default function DashboardPage() {
  const [filters, setFilters] = useState<TicketFilterValue>(EMPTY_FILTERS);

  const properties = useAsync(() => listProperties(), []);
  const tickets = useAsync(
    () =>
      listTickets({
        property_id: filters.propertyId || undefined,
        ticket_status: filters.status || undefined,
        category: filters.category || undefined,
      }),
    [filters.propertyId, filters.status, filters.category],
  );

  const propertyNames = useMemo(() => {
    const map = new Map<string, string>();
    properties.data?.forEach((property) => map.set(property.id, property.name));
    return map;
  }, [properties.data]);

  const ticketList = useMemo(() => tickets.data ?? [], [tickets.data]);

  // PENDING_UPLOAD and DISPATCHING both resolve in a background task with no push
  // channel, so the list refreshes itself while any row is still in motion.
  const hasPendingWork = ticketList.some((ticket) => isTransient(ticket.status));
  usePolling(hasPendingWork, () => void tickets.reload({ silent: true }), {
    intervalMs: 5000,
    maxTicks: 24,
  });

  const { needsAction, rest } = useMemo(() => {
    const needsActionList: Ticket[] = [];
    const restList: Ticket[] = [];

    ticketList.forEach((ticket) => {
      (isActionRequired(ticket.status) ? needsActionList : restList).push(ticket);
    });

    return { needsAction: needsActionList, rest: restList };
  }, [ticketList]);

  const filtersActive =
    Boolean(filters.propertyId) || Boolean(filters.status) || Boolean(filters.category);
  const hasProperties = (properties.data?.length ?? 0) > 0;
  const loading = tickets.loading || properties.loading;

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Tickets"
        description="Every ticket across every property you manage, newest first."
        action={
          <Button
            variant="secondary"
            size="sm"
            icon={<RefreshCw size={14} />}
            onClick={() => void tickets.reload()}
            disabled={tickets.loading}
          >
            Refresh
          </Button>
        }
      />

      {properties.error ? <Alert tone="danger">{properties.error}</Alert> : null}
      {tickets.error ? (
        <Alert tone="danger">
          {tickets.error}{" "}
          <button
            type="button"
            className="font-semibold underline"
            onClick={() => void tickets.reload()}
          >
            Try again
          </button>
        </Alert>
      ) : null}

      {hasProperties ? (
        <TicketFilters
          value={filters}
          properties={properties.data ?? []}
          onChange={setFilters}
        />
      ) : null}

      {loading && ticketList.length === 0 ? <RowsSkeleton rows={4} /> : null}

      {!loading && !hasProperties ? (
        <FadeIn>
          <EmptyState
            icon={<Building2 size={22} />}
            title="Add a property to get started"
            description="Tickets belong to properties, and tenants are invited per property. Nothing can arrive here until you've added your first one."
            action={
              <Link href="/properties">
                <Button>Add a property</Button>
              </Link>
            }
          />
        </FadeIn>
      ) : null}

      {!loading && hasProperties && ticketList.length === 0 ? (
        <FadeIn>
          {filtersActive ? (
            <EmptyState
              icon={<SearchX size={22} />}
              title="No tickets match these filters"
              description="Try widening the property, status, or category filter."
              action={
                <Button variant="secondary" onClick={() => setFilters(EMPTY_FILTERS)}>
                  Clear filters
                </Button>
              }
            />
          ) : (
            <EmptyState
              icon={<Inbox size={22} />}
              title="No tickets yet"
              description="When a tenant reports an issue it lands here already classified, with a priority and a plain-English summary."
            />
          )}
        </FadeIn>
      ) : null}

      {needsAction.length > 0 ? (
        <section className="rounded-2xl border border-warn/30 bg-warn-soft/40 p-5 shadow-card">
          <header className="mb-2.5 flex items-center gap-2">
            <TriangleAlert size={18} className="text-warn shrink-0" />
            <h2 className="text-base font-bold text-ink-strong">
              Needs your attention
              <span className="ml-2 text-technical font-normal text-muted">
                {needsAction.length}
              </span>
            </h2>
          </header>
          <p className="mb-4 text-xs font-medium text-muted leading-relaxed">
            Approval is paused, the AI escalated, or processing failed. Nothing moves
            on these until you act.
          </p>
          <StaggerList>
            {needsAction.map((ticket) => (
              <StaggerItem key={ticket.id}>
                <TicketRow
                  ticket={ticket}
                  propertyName={propertyNames.get(ticket.property_id)}
                />
              </StaggerItem>
            ))}
          </StaggerList>
        </section>
      ) : null}

      {rest.length > 0 ? (
        <section className="flex flex-col gap-3">
          {needsAction.length > 0 ? (
            <h2 className="text-base font-bold text-ink-strong">Everything else</h2>
          ) : null}
          <StaggerList>
            {rest.map((ticket) => (
              <StaggerItem key={ticket.id}>
                <TicketRow
                  ticket={ticket}
                  propertyName={propertyNames.get(ticket.property_id)}
                />
              </StaggerItem>
            ))}
          </StaggerList>
        </section>
      ) : null}
    </div>
  );
}
