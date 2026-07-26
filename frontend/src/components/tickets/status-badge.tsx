import { Badge } from "@/components/ui/badge";
import {
  categoryLabel,
  priorityLabel,
  priorityTone,
  statusLabel,
  statusTone,
  tenantStatusLabel,
} from "@/lib/status";
import type { TicketCategory, TicketPriority, TicketStatus } from "@/lib/types";

/** Internal status vocabulary — property-manager screens only. */
export function StatusBadge({ status }: { status: TicketStatus }) {
  return <Badge tone={statusTone(status)}>{statusLabel(status)}</Badge>;
}

/**
 * Tenant-facing status. Deliberately a separate component from StatusBadge so
 * the internal vocabulary can't leak into a tenant screen by accident.
 */
export function TenantStatusBadge({ status }: { status: TicketStatus }) {
  return <Badge tone={statusTone(status)}>{tenantStatusLabel(status)}</Badge>;
}

export function PriorityBadge({ priority }: { priority: TicketPriority }) {
  return <Badge tone={priorityTone(priority)}>{priorityLabel(priority)}</Badge>;
}

export function CategoryBadge({ category }: { category: TicketCategory | string }) {
  return <Badge tone="neutral">{categoryLabel(category)}</Badge>;
}
