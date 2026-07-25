/**
 * Wire types — one-to-one with the FastAPI Pydantic schemas in
 * backend/app/schemas/. Keep these in sync with the backend; nothing here is
 * derived or invented.
 */

export type Role = "pm" | "tenant" | "vendor";

export type InviteStatus = "pending" | "approved";

/** backend/app/core/categories.py :: TicketCategory */
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

export type TicketCategory = (typeof TICKET_CATEGORIES)[number];

/**
 * backend/app/core/categories.py :: VENDOR_CATEGORIES
 * "other" is a ticket-only catch-all and is rejected on vendor creation.
 */
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
  categories?: VendorCategory[] | null;
  max_concurrent_jobs: number;
}

// ─── Tickets ─────────────────────────────────────────────────────────────────

export interface Ticket {
  id: string;
  property_id: string;
  tenant_id: string;
  title: string;
  description: string | null;
  category: TicketCategory | null;
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
