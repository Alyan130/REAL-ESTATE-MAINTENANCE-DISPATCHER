/**
 * In-memory demo state.
 *
 * TEMPORARY — see fixtures.ts. Mutations are real for the life of the tab and
 * reset on reload, which is enough to exercise every flow the UI supports.
 */
import {
  DEMO_PROPERTIES,
  DEMO_TENANTS,
  DEMO_TICKETS,
  DEMO_USERS,
  demoPhoto,
  type DemoUser,
} from "@/lib/demo/fixtures";
import { DEMO_VENDORS } from "@/lib/demo/fixtures";
import type { Property, Tenant, Ticket, TicketCategory, Vendor } from "@/lib/types";

interface DemoState {
  users: DemoUser[];
  properties: Property[];
  tenants: Tenant[];
  vendors: Vendor[];
  tickets: Ticket[];
}

/** Deep-ish clone so the fixture arrays stay pristine across resets. */
function seed(): DemoState {
  return {
    users: DEMO_USERS.map((user) => ({ ...user })),
    properties: DEMO_PROPERTIES.map((property) => ({ ...property })),
    tenants: DEMO_TENANTS.map((tenant) => ({ ...tenant })),
    vendors: DEMO_VENDORS.map((vendor) => ({
      ...vendor,
      categories: vendor.categories ? [...vendor.categories] : null,
    })),
    tickets: DEMO_TICKETS.map((ticket) => ({
      ...ticket,
      media_urls: ticket.media_urls ? [...ticket.media_urls] : null,
    })),
  };
}

export const store: DemoState = seed();

export function newId(): string {
  return typeof crypto !== "undefined" && "randomUUID" in crypto
    ? crypto.randomUUID()
    : `${Date.now()}-${Math.random()}`;
}

export function nowIso(): string {
  return new Date().toISOString();
}

function touch(ticket: Ticket): void {
  ticket.updated_at = nowIso();
}

// ─── Simulated background work ───────────────────────────────────────────────

/**
 * Mirrors the real dispatch agent's rule: the highest-rated active vendor whose
 * `categories` contain the ticket's category wins, and a category nobody covers
 * escalates to NEEDS_ATTENTION.
 */
function hasVendorFor(category: TicketCategory | null): boolean {
  if (!category || category === "other") return false;
  return store.vendors.some(
    (vendor) => vendor.is_active && vendor.categories?.includes(category),
  );
}

const CLASSIFY_DELAY_MS = 4500;
const DISPATCH_DELAY_MS = 5000;

interface Classification {
  category: TicketCategory;
  priority: Ticket["priority"];
  summary: string;
}

/** Crude keyword triage — enough to make the AI step feel real in a demo. */
function classify(title: string, description: string | null): Classification {
  const text = `${title} ${description ?? ""}`.toLowerCase();

  const emergency = /(flood|pouring|gushing|burst|no heat|gas|smoke|sparks|electric shock)/.test(
    text,
  );

  const rules: [RegExp, TicketCategory][] = [
    [/(tap|leak|drip|water|toilet|sink|drain|pipe|boiler pressure)/, "plumbing"],
    [/(light|socket|power|electric|fuse|wiring|breaker)/, "electrical"],
    [/(heat|radiator|boiler|cold|air con|ac|ventilation|hvac)/, "hvac"],
    [/(crack|ceiling|wall|roof|damp|window frame|door frame|structural)/, "structural"],
    [/(fridge|freezer|oven|washing machine|dishwasher|dryer|appliance)/, "appliance"],
    [/(mouse|mice|rat|insect|ant|wasp|pest|cockroach)/, "pest"],
    [/(clean|rubbish|bins|litter|mould)/, "cleaning"],
  ];

  const category = rules.find(([pattern]) => pattern.test(text))?.[1] ?? "other";
  const priority = emergency ? "P1" : category === "other" ? "P4" : "P3";

  return {
    category,
    priority,
    summary: `${priority} ${category} — ${title.charAt(0).toLowerCase()}${title.slice(1)}. Classified from the tenant's report; ${
      category === "other"
        ? "no trade matched, so this needs your judgement."
        : "matched to the " + category + " trade."
    }`,
  };
}

/**
 * Photo upload plus classification, on a timer. The UI polls while the ticket is
 * PENDING_UPLOAD, so this is what makes that polling visible.
 */
export function scheduleClassification(ticketId: string, photoCount: number): void {
  setTimeout(() => {
    const ticket = store.tickets.find((candidate) => candidate.id === ticketId);
    if (!ticket || ticket.status !== "PENDING_UPLOAD") return;

    const { category, priority, summary } = classify(ticket.title, ticket.description);
    ticket.category = category;
    ticket.priority = priority;
    ticket.ai_summary = summary;
    ticket.media_urls =
      photoCount > 0
        ? Array.from({ length: photoCount }, (_, index) => demoPhoto(ticketId, index))
        : null;

    // P1 skips approval entirely and dispatches during intake.
    if (priority === "P1") {
      ticket.status = hasVendorFor(category) ? "DISPATCHED" : "NEEDS_ATTENTION";
    } else {
      ticket.status = "PENDING_APPROVAL";
    }

    touch(ticket);
  }, CLASSIFY_DELAY_MS);
}

/** Vendor selection after approval: DISPATCHING settles to DISPATCHED or NEEDS_ATTENTION. */
export function scheduleDispatch(ticketId: string): void {
  setTimeout(() => {
    const ticket = store.tickets.find((candidate) => candidate.id === ticketId);
    if (!ticket || ticket.status !== "DISPATCHING") return;

    ticket.status = hasVendorFor(ticket.category) ? "DISPATCHED" : "NEEDS_ATTENTION";
    touch(ticket);
  }, DISPATCH_DELAY_MS);
}

// ─── Lookups ─────────────────────────────────────────────────────────────────

export function findUserByEmail(email: string): DemoUser | undefined {
  return store.users.find(
    (user) => user.email.toLowerCase() === email.trim().toLowerCase(),
  );
}

export function findUserById(id: string): DemoUser | undefined {
  return store.users.find((user) => user.id === id);
}

export function emailInUse(email: string): boolean {
  const needle = email.trim().toLowerCase();
  return (
    store.users.some((user) => user.email.toLowerCase() === needle) ||
    store.tenants.some((tenant) => tenant.email.toLowerCase() === needle) ||
    store.vendors.some((vendor) => vendor.email?.toLowerCase() === needle)
  );
}

export function activeProperties(): Property[] {
  return store.properties.filter((property) => property.is_active);
}

export function activeTenants(): Tenant[] {
  return store.tenants.filter((tenant) => tenant.is_active);
}

export function activeVendors(): Vendor[] {
  return store.vendors.filter((vendor) => vendor.is_active);
}

export function ticketsNewestFirst(tickets: Ticket[]): Ticket[] {
  return [...tickets].sort((a, b) => b.created_at.localeCompare(a.created_at));
}
