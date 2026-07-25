/**
 * Demo fixtures.
 *
 * TEMPORARY — this whole `lib/demo/` folder exists so the UI can be reviewed
 * without a database. Delete it, the `NEXT_PUBLIC_DEMO_MODE` branch in
 * api-client.ts, and the DemoBadge once a real backend is reachable.
 */
import type { Property, Tenant, Ticket, Vendor } from "@/lib/types";

export interface DemoUser {
  id: string;
  email: string;
  password: string;
  name: string;
  role: "pm" | "tenant" | "vendor";
  /** The tenant profile behind this login, when the role is tenant. */
  tenantId?: string;
}

const hoursAgo = (hours: number): string =>
  new Date(Date.now() - hours * 3_600_000).toISOString();

const daysAgo = (days: number): string => hoursAgo(days * 24);

// ─── Accounts ────────────────────────────────────────────────────────────────

export const DEMO_PASSWORD = "demo1234";

export const DEMO_USERS: DemoUser[] = [
  {
    id: "11111111-1111-4111-8111-111111111111",
    email: "pm@demo.test",
    password: DEMO_PASSWORD,
    name: "Dana Whitfield",
    role: "pm",
  },
  {
    id: "22222222-2222-4222-8222-222222222222",
    email: "tenant@demo.test",
    password: DEMO_PASSWORD,
    name: "Priya Raman",
    role: "tenant",
    tenantId: "aaaaaaa1-0000-4000-8000-000000000001",
  },
  {
    id: "33333333-3333-4333-8333-333333333333",
    email: "vendor@demo.test",
    password: DEMO_PASSWORD,
    name: "Northgate Plumbing",
    role: "vendor",
  },
];

/** Signed in but never activated — demonstrates the ACCOUNT_PENDING branch. */
export const DEMO_PENDING_EMAIL = "sofia@demo.test";
/** Deactivated — demonstrates the ACCOUNT_DISABLED branch. */
export const DEMO_DISABLED_EMAIL = "disabled@demo.test";

const PM_ID = DEMO_USERS[0].id;

// ─── Properties ──────────────────────────────────────────────────────────────

export const DEMO_PROPERTIES: Property[] = [
  {
    id: "b0000001-0000-4000-8000-000000000001",
    pm_id: PM_ID,
    name: "Maple Court",
    address: "118 Maple Street, Springfield",
    is_active: true,
    created_at: daysAgo(210),
  },
  {
    id: "b0000002-0000-4000-8000-000000000002",
    pm_id: PM_ID,
    name: "Harbour View Apartments",
    address: "7 Quay Road, Bristol",
    is_active: true,
    created_at: daysAgo(96),
  },
  {
    id: "b0000003-0000-4000-8000-000000000003",
    pm_id: PM_ID,
    name: "Elm Street Duplex",
    address: "22 Elm Street, Springfield",
    is_active: true,
    created_at: daysAgo(38),
  },
];

// ─── Tenants ─────────────────────────────────────────────────────────────────

export const DEMO_TENANTS: Tenant[] = [
  {
    id: "aaaaaaa1-0000-4000-8000-000000000001",
    user_id: DEMO_USERS[1].id,
    email: "tenant@demo.test",
    name: "Priya Raman",
    property_id: DEMO_PROPERTIES[0].id,
    unit_number: "4B",
    lease_start: "2025-03-01",
    lease_end: "2027-02-28",
    invite_status: "approved",
    is_active: true,
  },
  {
    id: "aaaaaaa2-0000-4000-8000-000000000002",
    user_id: "44444444-4444-4444-8444-444444444444",
    email: "marcus@demo.test",
    name: "Marcus Bell",
    property_id: DEMO_PROPERTIES[0].id,
    unit_number: "2A",
    lease_start: "2024-09-15",
    lease_end: "2026-09-14",
    invite_status: "approved",
    is_active: true,
  },
  {
    id: "aaaaaaa3-0000-4000-8000-000000000003",
    user_id: "55555555-5555-4555-8555-555555555555",
    email: DEMO_PENDING_EMAIL,
    name: "Sofia Ortiz",
    property_id: DEMO_PROPERTIES[1].id,
    unit_number: "11",
    lease_start: "2026-07-01",
    lease_end: null,
    // Never accepted — this is the row that shows why "Invite pending" matters.
    invite_status: "pending",
    is_active: true,
  },
];

// ─── Vendors ─────────────────────────────────────────────────────────────────

/**
 * Deliberately leaves structural, appliance, and pest uncovered so the
 * coverage-gap warning on the vendors screen has something real to report.
 */
export const DEMO_VENDORS: Vendor[] = [
  {
    id: "c0000001-0000-4000-8000-000000000001",
    name: "Northgate Plumbing",
    email: "vendor@demo.test",
    phone: "+44 117 496 0021",
    categories: ["plumbing"],
    max_concurrent_jobs: 4,
    rating: 4.8,
    invite_status: "approved",
    is_active: true,
  },
  {
    id: "c0000002-0000-4000-8000-000000000002",
    name: "Volt & Co Electrical",
    email: "volt@demo.test",
    phone: "+44 117 496 0188",
    categories: ["electrical"],
    max_concurrent_jobs: 3,
    rating: 4.6,
    invite_status: "approved",
    is_active: true,
  },
  {
    id: "c0000003-0000-4000-8000-000000000003",
    name: "Sanjay Heating & Cooling",
    email: "sanjay@demo.test",
    phone: null,
    categories: ["hvac", "appliance"],
    max_concurrent_jobs: 2,
    rating: 4.9,
    invite_status: "pending",
    is_active: true,
  },
  {
    id: "c0000004-0000-4000-8000-000000000004",
    name: "CleanSweep Services",
    email: "cleansweep@demo.test",
    phone: "+44 117 496 0455",
    categories: ["cleaning"],
    max_concurrent_jobs: 6,
    rating: 4.2,
    invite_status: "approved",
    is_active: true,
  },
];

// ─── Tickets ─────────────────────────────────────────────────────────────────

const photo = (seed: string, index: number): string =>
  `https://picsum.photos/seed/${seed}-${index}/960/720`;

const PRIYA = DEMO_TENANTS[0].id;
const MARCUS = DEMO_TENANTS[1].id;
const SOFIA = DEMO_TENANTS[2].id;

export const DEMO_TICKETS: Ticket[] = [
  {
    id: "d0000001-0000-4000-8000-000000000001",
    property_id: DEMO_PROPERTIES[0].id,
    tenant_id: PRIYA,
    title: "Kitchen tap won't stop dripping",
    description:
      "It started Tuesday evening. Turning it off tight slows it but doesn't stop it — about a drip a second overnight, and the cupboard underneath is damp.",
    category: "plumbing",
    priority: "P2",
    status: "PENDING_APPROVAL",
    media_urls: [photo("tap", 1), photo("tap", 2)],
    ai_summary:
      "P2 plumbing — continuous drip from the kitchen mixer tap with damp forming in the cupboard below. Needs a washer or cartridge replacement before the unit is damaged.",
    permission_to_enter: true,
    created_at: hoursAgo(5),
    updated_at: hoursAgo(4),
  },
  {
    id: "d0000002-0000-4000-8000-000000000002",
    property_id: DEMO_PROPERTIES[0].id,
    tenant_id: MARCUS,
    title: "Hallway light flickers when the heating comes on",
    description:
      "Only happens when the boiler fires up. The light dims for a second then flickers for about a minute.",
    category: "electrical",
    priority: "P3",
    status: "PENDING_APPROVAL",
    media_urls: [],
    ai_summary:
      "P3 electrical — hallway lighting flickers in sync with boiler startup, suggesting a shared circuit under load. Worth an electrician checking the consumer unit.",
    permission_to_enter: false,
    created_at: hoursAgo(28),
    updated_at: hoursAgo(27),
  },
  {
    id: "d0000003-0000-4000-8000-000000000003",
    property_id: DEMO_PROPERTIES[1].id,
    tenant_id: SOFIA,
    title: "Crack has appeared above the bedroom window",
    description:
      "Roughly 40cm long, running diagonally from the corner of the frame. It wasn't there when I moved in.",
    category: "structural",
    priority: "P2",
    // No structural vendor exists in the pool, which is exactly why this escalated.
    status: "NEEDS_ATTENTION",
    media_urls: [photo("crack", 1)],
    ai_summary:
      "P2 structural — diagonal crack above a bedroom window frame, length ~40cm. No structural vendor is available in the pool, so this needs manual assignment.",
    permission_to_enter: true,
    created_at: daysAgo(2),
    updated_at: daysAgo(2),
  },
  {
    id: "d0000004-0000-4000-8000-000000000004",
    property_id: DEMO_PROPERTIES[0].id,
    tenant_id: PRIYA,
    title: "Water coming through the ceiling in the bathroom",
    description: "It's running, not dripping. I've put a bucket under it.",
    category: "plumbing",
    priority: "P1",
    // P1 auto-dispatches during intake — it never waits for approval.
    status: "DISPATCHED",
    media_urls: [photo("leak", 1), photo("leak", 2), photo("leak", 3)],
    ai_summary:
      "P1 plumbing — active water ingress through the bathroom ceiling from the flat above. Emergency: dispatched immediately without waiting for approval.",
    permission_to_enter: true,
    created_at: daysAgo(4),
    updated_at: daysAgo(4),
  },
  {
    id: "d0000005-0000-4000-8000-000000000005",
    property_id: DEMO_PROPERTIES[2].id,
    tenant_id: MARCUS,
    title: "Communal stairwell hasn't been cleaned in three weeks",
    description: null,
    category: "cleaning",
    priority: "P4",
    status: "TRIAGED",
    media_urls: [],
    ai_summary:
      "P4 cleaning — communal stairwell missed on the regular schedule for roughly three weeks. Routine, no access needed.",
    permission_to_enter: false,
    created_at: daysAgo(6),
    updated_at: daysAgo(6),
  },
  {
    id: "d0000006-0000-4000-8000-000000000006",
    property_id: DEMO_PROPERTIES[1].id,
    tenant_id: SOFIA,
    title: "Radiator in the living room stays cold",
    description: "The rest of the flat heats up fine. Bled it twice, no change.",
    category: "hvac",
    priority: "P3",
    status: "DISPATCHED",
    media_urls: [],
    ai_summary:
      "P3 hvac — single radiator not heating while the rest of the system works, and bleeding hasn't helped. Likely a stuck valve.",
    permission_to_enter: false,
    created_at: daysAgo(9),
    updated_at: daysAgo(8),
  },
  {
    id: "d0000007-0000-4000-8000-000000000007",
    property_id: DEMO_PROPERTIES[0].id,
    tenant_id: PRIYA,
    title: "Front door lock is sticking",
    description: "Takes a lot of jiggling to get the key to turn.",
    category: null,
    priority: null,
    // Background processing crashed — distinct from NEEDS_ATTENTION, nothing escalated.
    status: "ERROR",
    media_urls: [],
    ai_summary: null,
    permission_to_enter: false,
    created_at: daysAgo(11),
    updated_at: daysAgo(11),
  },
  {
    id: "d0000008-0000-4000-8000-000000000008",
    property_id: DEMO_PROPERTIES[0].id,
    tenant_id: PRIYA,
    title: "Neighbour's bins left in the shared entryway",
    description: "Been there since the weekend, blocking the pushchair space.",
    category: "other",
    priority: "P4",
    status: "CANCELLED",
    media_urls: [],
    ai_summary:
      "P4 other — bins obstructing a shared entryway. Not a maintenance fault; handled as a neighbour matter.",
    permission_to_enter: false,
    created_at: daysAgo(15),
    updated_at: daysAgo(14),
  },
];

export const demoPhoto = photo;
