import type { TicketCategory, TicketPriority, TicketStatus } from "@/lib/types";

export type Tone = "neutral" | "info" | "brand" | "warn" | "danger" | "success";

// ─── Status ──────────────────────────────────────────────────────────────────

/** Internal vocabulary — property-manager facing only. */
const PM_STATUS_LABELS: Record<TicketStatus, string> = {
  PENDING_UPLOAD: "Pending upload",
  OPEN: "Open",
  TRIAGED: "Triaged",
  PENDING_APPROVAL: "Pending approval",
  DISPATCHING: "Dispatching",
  DISPATCHED: "Dispatched",
  CANCELLED: "Cancelled",
  NEEDS_ATTENTION: "Needs attention",
  ERROR: "Error",
  QUOTED: "Quoted",
  APPROVED: "Approved",
  SCHEDULED: "Scheduled",
  IN_PROGRESS: "In progress",
  COMPLETED: "Completed",
  INVOICED: "Invoiced",
  CLOSED: "Closed",
};

/**
 * Tenant-facing translations.
 *
 * Two rules from docs/context/screens.md are encoded here: internal vocabulary
 * is never shown to a tenant, and `ERROR` is never surfaced as a failure — a
 * tenant reads that their manager is looking at it, which is what happens next.
 */
const TENANT_STATUS_LABELS: Record<TicketStatus, string> = {
  PENDING_UPLOAD: "Uploading your photos",
  OPEN: "Received",
  TRIAGED: "Reviewing your report",
  PENDING_APPROVAL: "Waiting on your property manager",
  DISPATCHING: "Finding a contractor",
  DISPATCHED: "Contractor assigned",
  CANCELLED: "Closed — no work scheduled",
  NEEDS_ATTENTION: "Your property manager is reviewing this",
  ERROR: "Your property manager is reviewing this",
  QUOTED: "Getting a price",
  APPROVED: "Work approved",
  SCHEDULED: "Visit scheduled",
  IN_PROGRESS: "Work underway",
  COMPLETED: "Work completed",
  INVOICED: "Wrapping up",
  CLOSED: "Resolved",
};

const STATUS_TONES: Record<TicketStatus, Tone> = {
  PENDING_UPLOAD: "neutral",
  OPEN: "info",
  TRIAGED: "info",
  PENDING_APPROVAL: "warn",
  DISPATCHING: "brand",
  DISPATCHED: "success",
  CANCELLED: "neutral",
  NEEDS_ATTENTION: "danger",
  ERROR: "danger",
  QUOTED: "info",
  APPROVED: "success",
  SCHEDULED: "info",
  IN_PROGRESS: "brand",
  COMPLETED: "success",
  INVOICED: "info",
  CLOSED: "neutral",
};

/** Statuses the PM can filter by — the ones the backend actually sets today. */
export const ACTIVE_STATUSES: TicketStatus[] = [
  "PENDING_UPLOAD",
  "OPEN",
  "TRIAGED",
  "PENDING_APPROVAL",
  "DISPATCHING",
  "DISPATCHED",
  "CANCELLED",
  "NEEDS_ATTENTION",
  "ERROR",
];

/** Every status the PM may set through the manual override. */
export const ALL_STATUSES = Object.keys(PM_STATUS_LABELS) as TicketStatus[];

/**
 * The three states that make the PM the blocker. Kept in priority order —
 * the dashboard renders them as its "needs action" band.
 */
export const ACTION_REQUIRED_STATUSES: TicketStatus[] = [
  "PENDING_APPROVAL",
  "QUOTED",
  "NEEDS_ATTENTION",
  "ERROR",
];

export function statusLabel(status: TicketStatus): string {
  return PM_STATUS_LABELS[status] ?? status;
}

export function tenantStatusLabel(status: TicketStatus): string {
  return TENANT_STATUS_LABELS[status] ?? "In progress";
}

export function statusTone(status: TicketStatus): Tone {
  return STATUS_TONES[status] ?? "neutral";
}

export function isActionRequired(status: TicketStatus): boolean {
  return ACTION_REQUIRED_STATUSES.includes(status);
}

/** Statuses where the backend is still working and the row will change on its own. */
export function isTransient(status: TicketStatus): boolean {
  return status === "PENDING_UPLOAD" || status === "DISPATCHING";
}

/** One-line explanation of what is happening, for the PM ticket detail. */
export const STATUS_EXPLANATIONS: Partial<Record<TicketStatus, string>> = {
  PENDING_UPLOAD:
    "Photos are still uploading and the AI hasn't classified this yet. Category, priority, and summary will fill in shortly.",
  PENDING_APPROVAL:
    "The AI is paused waiting on your decision. Nothing moves until you approve or reject.",
  DISPATCHING:
    "Vendor selection is running in the background. This page updates itself as soon as it finishes.",
  DISPATCHED:
    "A vendor has been offered this job and is being asked for a price. You'll be brought in if the quote needs a decision.",
  QUOTED:
    "A vendor has quoted and it needs your call. The negotiation is paused until you accept, counter, or move to another vendor.",
  APPROVED:
    "The quote is agreed and the vendor has the job details. Nothing is waiting on you.",
  NEEDS_ATTENTION:
    "The AI escalated this: no vendor was available, or approval processing failed. It needs you to act manually.",
  ERROR:
    "Background processing crashed before this ticket was escalated. Nothing was sent to a vendor.",
  CANCELLED: "This ticket was rejected and no work was scheduled.",
};

// ─── Priority ────────────────────────────────────────────────────────────────

const PRIORITY_LABELS: Record<TicketPriority, string> = {
  P1: "P1 Emergency",
  P2: "P2",
  P3: "P3",
  P4: "P4",
};

const PRIORITY_TONES: Record<TicketPriority, Tone> = {
  P1: "danger",
  P2: "warn",
  P3: "info",
  P4: "neutral",
};

export function priorityLabel(priority: TicketPriority): string {
  return PRIORITY_LABELS[priority] ?? priority;
}

export function priorityTone(priority: TicketPriority): Tone {
  return PRIORITY_TONES[priority] ?? "neutral";
}

// ─── Category ────────────────────────────────────────────────────────────────

const CATEGORY_LABELS: Record<TicketCategory, string> = {
  plumbing: "Plumbing",
  electrical: "Electrical",
  hvac: "HVAC",
  structural: "Structural",
  appliance: "Appliance",
  pest: "Pest",
  cleaning: "Cleaning",
  other: "Other",
};

/**
 * Display name for a category slug.
 *
 * Categories are PM-editable, so a slug the seed list has never heard of ("dry-
 * lining") is normal rather than an error. Those get title-cased here so a
 * custom category doesn't render as a raw slug next to the built-in ones. The
 * PM's own label is authoritative where a `CategorySetting` is on hand — use
 * that in preference to this.
 */
export function categoryLabel(category: string): string {
  const known = CATEGORY_LABELS[category as TicketCategory];
  if (known) return known;

  return category
    .split(/[-_\s]+/)
    .filter(Boolean)
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}
