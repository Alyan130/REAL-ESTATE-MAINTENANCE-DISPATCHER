/**
 * Wire types — one-to-one with the FastAPI Pydantic schemas in
 * backend/app/schemas/. Keep these in sync with the backend; nothing here is
 * derived or invented.
 */

export type Role = "pm" | "tenant" | "vendor";

export type InviteStatus = "pending" | "approved";

/**
 * backend/app/core/categories.py :: SEED_CATEGORIES
 *
 * The starter vocabulary only. Categories are per-PM and editable — the real
 * list comes from `GET /categories`, so a PM may have trades that aren't here.
 * These constants remain for labels and as a fallback before the fetch lands;
 * never use them to constrain what a user may pick.
 */
export const TICKET_CATEGORIES = [
  "plumbing",
  "electrical",
  "hvac",
  "structural",
  "appliance",
  "pest",
  "cleaning",
  "other",
] as const;

/** A seed slug. A live category is a plain `string` — see `CategorySetting`. */
export type TicketCategory = (typeof TICKET_CATEGORIES)[number];

/** "other" is the intake fallback and is rejected on vendor creation. */
export const VENDOR_CATEGORIES = TICKET_CATEGORIES.filter(
  (category): category is Exclude<TicketCategory, "other"> => category !== "other",
);

export type VendorCategory = (typeof VENDOR_CATEGORIES)[number];

/**
 * Statuses the backend actually sets today. The tail of the lifecycle
 * (QUOTED..CLOSED) exists in the data model but nothing writes it yet — it is
 * listed so the UI renders rather than breaks if a value shows up.
 */
export type TicketStatus =
  | "PENDING_UPLOAD"
  | "OPEN"
  | "TRIAGED"
  | "PENDING_APPROVAL"
  | "DISPATCHING"
  | "DISPATCHED"
  | "CANCELLED"
  | "NEEDS_ATTENTION"
  | "ERROR"
  | "QUOTED"
  | "APPROVED"
  | "SCHEDULED"
  | "IN_PROGRESS"
  | "COMPLETED"
  | "INVOICED"
  | "CLOSED";

export type TicketPriority = "P1" | "P2" | "P3" | "P4";

// ─── Auth ────────────────────────────────────────────────────────────────────

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface AcceptInviteRequest {
  token: string;
  password: string;
  confirm_password: string;
}

// ─── Properties ──────────────────────────────────────────────────────────────

export interface Property {
  id: string;
  pm_id: string;
  name: string;
  address: string;
  is_active: boolean;
  created_at: string;
}

export interface CreatePropertyRequest {
  name: string;
  address: string;
}

// ─── Tenants ─────────────────────────────────────────────────────────────────

export interface Tenant {
  id: string;
  user_id: string;
  email: string;
  name: string | null;
  property_id: string;
  unit_number: string | null;
  lease_start: string | null;
  lease_end: string | null;
  invite_status: InviteStatus;
  is_active: boolean;
}

export interface CreateTenantRequest {
  name: string;
  email: string;
  property_id: string;
  unit_number?: string | null;
  lease_start?: string | null;
  lease_end?: string | null;
}

// ─── Vendors ─────────────────────────────────────────────────────────────────

export interface Vendor {
  id: string;
  name: string;
  email: string | null;
  phone: string | null;
  categories: string[] | null;
  max_concurrent_jobs: number;
  rating: number;
  invite_status: InviteStatus;
  is_active: boolean;
}

export interface CreateVendorRequest {
  name: string;
  email: string;
  phone?: string | null;
  /** Slugs from the PM's own categories — 400 UNKNOWN_CATEGORY if one isn't. */
  categories?: string[] | null;
  max_concurrent_jobs: number;
}

// ─── Categories ──────────────────────────────────────────────────────────────

/**
 * backend/app/schemas/categories.py :: CategoryResponse
 *
 * `name` is the slug that lands in `Ticket.category` and `Vendor.categories`.
 * `max_price` is the auto-approve ceiling — null means the PM is asked about
 * every quote in this category.
 */
export interface CategorySetting {
  id: string;
  name: string;
  label: string;
  target_price: number | null;
  max_price: number | null;
  is_vendor_selectable: boolean;
  sort_order: number;
}

export interface CreateCategoryRequest {
  label: string;
  name?: string;
  target_price?: number | null;
  max_price?: number | null;
}

export interface UpdateCategoryRequest {
  label?: string;
  target_price?: number | null;
  max_price?: number | null;
  sort_order?: number;
}

// ─── Tickets ─────────────────────────────────────────────────────────────────

export interface Ticket {
  id: string;
  property_id: string;
  tenant_id: string;
  title: string;
  description: string | null;
  /** A slug from the PM's categories — not limited to the seed vocabulary. */
  category: string | null;
  priority: TicketPriority | null;
  status: TicketStatus;
  media_urls: string[] | null;
  ai_summary: string | null;
  permission_to_enter: boolean;
  created_at: string;
  updated_at: string;
}

export interface TicketCreatedResponse {
  id: string;
  message: string;
}

export interface StatusUpdateResponse {
  id: string;
  status: TicketStatus;
}

export interface TicketFilters {
  property_id?: string;
  ticket_status?: string;
  category?: string;
}

export interface CreateTicketRequest {
  title: string;
  description?: string;
  permission_to_enter: boolean;
  photos: File[];
}

// ─── Negotiation ─────────────────────────────────────────────────────────────

/** backend/app/schemas/negotiation.py :: MessageResponse */
export interface NegotiationMessage {
  id: string;
  sender: "ai" | "vendor" | "system";
  body: string;
  created_at: string;
}

/**
 * backend/app/schemas/negotiation.py :: VendorChatResponse
 *
 * The vendor's view, served from an unauthenticated token link. It deliberately
 * carries no street address, no ceiling, and no other vendor's quote — only what
 * is needed to price the work. The address ships with the confirmation email
 * once the job is approved.
 */
export interface VendorChat {
  vendor_job_id: string;
  vendor_name: string;
  ticket_title: string;
  ticket_summary: string;
  category_label: string;
  priority_label: string;
  property_label: string;
  access_note: string;
  media_urls: string[];
  status: string;
  /** False once the job is settled — history stays readable, replies don't. */
  can_reply: boolean;
  messages: NegotiationMessage[];
}

/** 202 — the message is stored; the AI's answer arrives on a later poll. */
export interface MessageAccepted {
  id: string;
  created_at: string;
}

/**
 * backend/app/schemas/negotiation.py :: NegotiationResponse
 *
 * The PM's decision card. Separate from `VendorChat` on purpose: this one
 * carries the ceiling, and sharing a type would make leaking it to the vendor's
 * public page a one-line mistake.
 */
export interface Negotiation {
  vendor_job_id: string;
  vendor_name: string;
  vendor_rating: number | null;
  status: string;
  quoted_price: number | null;
  availability: string | null;
  target_price: number | null;
  max_price: number | null;
  suggested_counter: number | null;
  decision_reason: string | null;
  counter_rounds_used: number;
  counter_allowed: boolean;
  awaiting_decision: boolean;
  messages: NegotiationMessage[];
}

export type NegotiationAction = "accept" | "counter" | "next_vendor";

export interface NegotiationDecisionRequest {
  action: NegotiationAction;
  counter_price?: number | null;
}
