/**
 * Axios adapter that answers every API call from the in-memory demo store.
 *
 * TEMPORARY — see fixtures.ts. It plugs in at the transport layer precisely so
 * no screen, store, or api/ module knows it exists: the code paths exercised in
 * demo mode are the same ones that will talk to FastAPI.
 *
 * Error responses use the real envelope ({error, code}) and the real status
 * codes, so the UI's error branches are genuinely exercised too.
 */
import { AxiosError, type AxiosAdapter, type AxiosResponse, type InternalAxiosRequestConfig } from "axios";

import {
  DEMO_DISABLED_EMAIL,
  DEMO_PENDING_EMAIL,
  type DemoUser,
} from "@/lib/demo/fixtures";
import {
  activeProperties,
  activeTenants,
  activeVendors,
  emailInUse,
  findUserByEmail,
  findUserById,
  newId,
  nowIso,
  scheduleClassification,
  scheduleDispatch,
  store,
  ticketsNewestFirst,
} from "@/lib/demo/demo-store";
import { decodeToken } from "@/lib/jwt";
import type { Property, Tenant, Ticket, Vendor } from "@/lib/types";

const LATENCY_MS = 260;

// ─── Failure signalling ──────────────────────────────────────────────────────

class DemoFailure extends Error {
  constructor(
    readonly status: number,
    readonly code: string,
    message: string,
  ) {
    super(message);
  }
}

const fail = (status: number, code: string, message: string): never => {
  throw new DemoFailure(status, code, message);
};

// ─── Token minting ───────────────────────────────────────────────────────────

const base64url = (value: string): string =>
  btoa(value).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");

/**
 * A structurally valid JWT with a junk signature. Nothing in the frontend
 * verifies signatures — it only reads `sub` and `role` — and nothing here ever
 * reaches a real API.
 */
function mintToken(user: DemoUser): string {
  const now = Math.floor(Date.now() / 1000);
  const header = base64url(JSON.stringify({ alg: "HS256", typ: "JWT" }));
  const payload = base64url(
    JSON.stringify({
      sub: user.id,
      role: user.role,
      type: "login",
      iat: now,
      exp: now + 60 * 60 * 24 * 60,
    }),
  );
  return `${header}.${payload}.demo-signature-not-verified`;
}

// ─── Request helpers ─────────────────────────────────────────────────────────

function readBody(config: InternalAxiosRequestConfig): Record<string, unknown> {
  const { data } = config;
  if (!data) return {};
  if (typeof data === "string") {
    try {
      return JSON.parse(data) as Record<string, unknown>;
    } catch {
      return {};
    }
  }
  return data as Record<string, unknown>;
}

function currentUser(config: InternalAxiosRequestConfig): DemoUser {
  const header = String(config.headers?.Authorization ?? "");
  const token = header.replace(/^Bearer\s+/i, "");
  const claims = token ? decodeToken(token) : null;
  const user = claims ? findUserById(claims.sub) : undefined;

  if (!user) {
    fail(401, "NOT_AUTHENTICATED", "Could not validate credentials.");
  }
  return user!;
}

function requirePm(config: InternalAxiosRequestConfig): DemoUser {
  const user = currentUser(config);
  if (user.role !== "pm") {
    fail(403, "FORBIDDEN", "Property manager access required.");
  }
  return user;
}

// ─── Route table ─────────────────────────────────────────────────────────────

interface RouteContext {
  config: InternalAxiosRequestConfig;
  body: Record<string, unknown>;
  params: Record<string, string>;
  path: string[];
}

type Handler = (ctx: RouteContext) => unknown;

const routes: [string, RegExp, Handler][] = [
  // ── Auth ──
  [
    "POST",
    /^\/auth\/login$/,
    ({ body }) => {
      const email = String(body.email ?? "").trim().toLowerCase();
      const password = String(body.password ?? "");

      if (email === DEMO_PENDING_EMAIL) {
        fail(403, "ACCOUNT_PENDING", "Your account is pending approval.");
      }
      if (email === DEMO_DISABLED_EMAIL) {
        fail(401, "ACCOUNT_DISABLED", "Account is disabled.");
      }

      const user = findUserByEmail(email);
      if (!user || user.password !== password) {
        fail(401, "INVALID_CREDENTIALS", "Invalid email or password.");
      }

      return { access_token: mintToken(user!), token_type: "bearer" };
    },
  ],
  [
    "POST",
    /^\/auth\/accept-invite$/,
    ({ body }) => {
      const token = String(body.token ?? "");
      const password = String(body.password ?? "");
      const confirm = String(body.confirm_password ?? "");

      if (password !== confirm) {
        fail(400, "PASSWORD_MISMATCH", "Passwords do not match.");
      }

      // Magic tokens so every invite error state can be demonstrated:
      //   ?token=expired | superseded | used | bad
      if (token === "expired") fail(410, "INVITE_EXPIRED", "Invite token has expired.");
      if (token === "superseded") {
        fail(410, "INVITE_SUPERSEDED", "Invite token has been superseded.");
      }
      if (token === "used") {
        fail(400, "INVITE_ALREADY_ACCEPTED", "Invite already accepted.");
      }
      if (token === "bad") fail(400, "INVALID_TOKEN", "Invalid invite token.");

      // Any other token activates the pending tenant and signs them in.
      const pending = store.tenants.find(
        (tenant) => tenant.email === DEMO_PENDING_EMAIL,
      );
      if (pending) pending.invite_status = "approved";

      const user: DemoUser = {
        id: pending?.user_id ?? newId(),
        email: pending?.email ?? "new.tenant@demo.test",
        password,
        name: pending?.name ?? "New Tenant",
        role: "tenant",
        tenantId: pending?.id,
      };

      if (!findUserById(user.id)) store.users.push(user);
      return { access_token: mintToken(user), token_type: "bearer" };
    },
  ],

  // ── Invites ──
  [
    "POST",
    /^\/auth\/invites\/tenants$/,
    ({ config, body }) => {
      requirePm(config);
      const email = String(body.email ?? "").trim();

      if (emailInUse(email)) {
        fail(400, "DUPLICATE_EMAIL", "A user with this email already exists.");
      }

      const propertyId = String(body.property_id ?? "");
      if (!activeProperties().some((property) => property.id === propertyId)) {
        fail(404, "NOT_FOUND", "Property not found.");
      }

      const tenant: Tenant = {
        id: newId(),
        user_id: newId(),
        email,
        name: String(body.name ?? ""),
        property_id: propertyId,
        unit_number: (body.unit_number as string) ?? null,
        lease_start: (body.lease_start as string) ?? null,
        lease_end: (body.lease_end as string) ?? null,
        invite_status: "pending",
        is_active: true,
      };
      store.tenants.push(tenant);
      return tenant;
    },
  ],
  [
    "POST",
    /^\/auth\/invites\/vendors$/,
    ({ config, body }) => {
      requirePm(config);
      const email = String(body.email ?? "").trim();

      if (emailInUse(email)) {
        fail(400, "DUPLICATE_EMAIL", "A user with this email already exists.");
      }

      const vendor: Vendor = {
        id: newId(),
        name: String(body.name ?? ""),
        email,
        phone: (body.phone as string) ?? null,
        categories: (body.categories as string[]) ?? null,
        max_concurrent_jobs: Number(body.max_concurrent_jobs ?? 3),
        rating: 5,
        invite_status: "pending",
        is_active: true,
      };
      store.vendors.push(vendor);
      return vendor;
    },
  ],
  [
    "POST",
    /^\/auth\/invites\/tenants\/([^/]+)\/resend$/,
    ({ config, path }) => {
      requirePm(config);
      const tenant = store.tenants.find((candidate) => candidate.id === path[0]);
      if (!tenant) fail(404, "NOT_FOUND", "Tenant not found.");
      if (tenant!.invite_status !== "pending") {
        fail(400, "INVITE_ALREADY_ACCEPTED", "Invite already accepted.");
      }
      return { ok: true };
    },
  ],
  [
    "POST",
    /^\/auth\/invites\/vendors\/([^/]+)\/resend$/,
    ({ config, path }) => {
      requirePm(config);
      const vendor = store.vendors.find((candidate) => candidate.id === path[0]);
      if (!vendor) fail(404, "NOT_FOUND", "Vendor not found.");
      if (vendor!.invite_status !== "pending") {
        fail(400, "INVITE_ALREADY_ACCEPTED", "Invite already accepted.");
      }
      return { ok: true };
    },
  ],

  // ── Properties ──
  [
    "GET",
    /^\/properties\/?$/,
    ({ config }) => {
      requirePm(config);
      return activeProperties();
    },
  ],
  [
    "POST",
    /^\/properties\/?$/,
    ({ config, body }) => {
      const pm = requirePm(config);
      const property: Property = {
        id: newId(),
        pm_id: pm.id,
        name: String(body.name ?? ""),
        address: String(body.address ?? ""),
        is_active: true,
        created_at: nowIso(),
      };
      store.properties.unshift(property);
      return property;
    },
  ],
  [
    "GET",
    /^\/properties\/([^/]+)$/,
    ({ config, path }) => {
      requirePm(config);
      const property = activeProperties().find((candidate) => candidate.id === path[0]);
      if (!property) fail(404, "NOT_FOUND", "Property not found.");
      return property;
    },
  ],
  [
    "DELETE",
    /^\/properties\/([^/]+)$/,
    ({ config, path }) => {
      requirePm(config);
      const property = store.properties.find((candidate) => candidate.id === path[0]);
      if (!property?.is_active) fail(404, "NOT_FOUND", "Property not found.");
      property!.is_active = false;
      return null;
    },
  ],

  // ── Tenants ──
  [
    "GET",
    /^\/tenants\/?$/,
    ({ config, params }) => {
      requirePm(config);
      const propertyId = params.property_id;
      return activeTenants().filter(
        (tenant) => !propertyId || tenant.property_id === propertyId,
      );
    },
  ],
  [
    "GET",
    /^\/tenants\/([^/]+)$/,
    ({ config, path }) => {
      requirePm(config);
      const tenant = activeTenants().find((candidate) => candidate.id === path[0]);
      if (!tenant) fail(404, "NOT_FOUND", "Tenant not found.");
      return tenant;
    },
  ],
  [
    "DELETE",
    /^\/tenants\/([^/]+)$/,
    ({ config, path }) => {
      requirePm(config);
      const tenant = store.tenants.find((candidate) => candidate.id === path[0]);
      if (!tenant?.is_active) fail(404, "NOT_FOUND", "Tenant not found.");
      tenant!.is_active = false;
      return null;
    },
  ],

  // ── Vendors ──
  [
    "GET",
    /^\/vendors\/?$/,
    ({ config }) => {
      requirePm(config);
      return activeVendors();
    },
  ],
  [
    "GET",
    /^\/vendors\/([^/]+)$/,
    ({ config, path }) => {
      requirePm(config);
      const vendor = activeVendors().find((candidate) => candidate.id === path[0]);
      if (!vendor) fail(404, "NOT_FOUND", "Vendor not found.");
      return vendor;
    },
  ],
  [
    "DELETE",
    /^\/vendors\/([^/]+)$/,
    ({ config, path }) => {
      requirePm(config);
      const vendor = store.vendors.find((candidate) => candidate.id === path[0]);
      if (!vendor?.is_active) fail(404, "NOT_FOUND", "Vendor not found.");
      vendor!.is_active = false;
      return null;
    },
  ],

  // ── Tickets ──
  [
    "POST",
    /^\/tickets\/?$/,
    ({ config }) => {
      const user = currentUser(config);
      if (user.role !== "tenant") {
        fail(403, "FORBIDDEN", "Only tenants can create tickets.");
      }

      const form = config.data as FormData;
      const tenant = store.tenants.find((candidate) => candidate.id === user.tenantId);
      if (!tenant) fail(404, "NOT_FOUND", "Tenant profile not found.");

      const photos = form.getAll("photos").filter((entry) => entry instanceof File);
      const ticket: Ticket = {
        id: newId(),
        property_id: tenant!.property_id,
        tenant_id: tenant!.id,
        title: String(form.get("title") ?? ""),
        description: (form.get("description") as string) || null,
        category: null,
        priority: null,
        // Matches the backend: no photos means no background job at all.
        status: photos.length > 0 ? "PENDING_UPLOAD" : "OPEN",
        media_urls: null,
        ai_summary: null,
        permission_to_enter: form.get("permission_to_enter") === "true",
        created_at: nowIso(),
        updated_at: nowIso(),
      };
      store.tickets.unshift(ticket);

      if (photos.length > 0) {
        scheduleClassification(ticket.id, photos.length);
      }

      return { id: ticket.id, message: "Ticket received. Processing in background." };
    },
  ],
  [
    "GET",
    /^\/tickets\/?$/,
    ({ config, params }) => {
      const user = currentUser(config);

      if (user.role === "tenant") {
        return ticketsNewestFirst(
          store.tickets.filter((ticket) => ticket.tenant_id === user.tenantId),
        );
      }
      if (user.role !== "pm") fail(403, "FORBIDDEN", "Access denied.");

      const filtered = store.tickets.filter((ticket) => {
        if (params.property_id && ticket.property_id !== params.property_id) return false;
        if (params.ticket_status && ticket.status !== params.ticket_status) return false;
        if (params.category && ticket.category !== params.category) return false;
        return true;
      });
      return ticketsNewestFirst(filtered);
    },
  ],
  [
    "GET",
    /^\/tickets\/([^/]+)$/,
    ({ config, path }) => {
      const user = currentUser(config);
      const ticket = store.tickets.find((candidate) => candidate.id === path[0]);
      if (!ticket) fail(404, "NOT_FOUND", "Ticket not found.");

      if (user.role === "tenant" && ticket!.tenant_id !== user.tenantId) {
        fail(403, "FORBIDDEN", "You do not have access to this ticket.");
      }
      return ticket;
    },
  ],
  [
    "PATCH",
    /^\/tickets\/([^/]+)\/status$/,
    ({ config, path, body }) => {
      requirePm(config);
      const ticket = store.tickets.find((candidate) => candidate.id === path[0]);
      if (!ticket) fail(404, "NOT_FOUND", "Ticket not found.");

      ticket!.status = String(body.status) as Ticket["status"];
      ticket!.updated_at = nowIso();
      return { id: ticket!.id, status: ticket!.status };
    },
  ],
  [
    "POST",
    /^\/tickets\/([^/]+)\/approve$/,
    ({ config, path }) => {
      requirePm(config);
      const ticket = store.tickets.find((candidate) => candidate.id === path[0]);
      if (!ticket) fail(404, "NOT_FOUND", "Ticket not found.");

      if (ticket!.status !== "PENDING_APPROVAL") {
        fail(
          409,
          "TICKET_NOT_AWAITING_APPROVAL",
          `Ticket is not awaiting approval (status: ${ticket!.status}).`,
        );
      }

      ticket!.status = "DISPATCHING";
      ticket!.updated_at = nowIso();
      scheduleDispatch(ticket!.id);

      return { id: ticket!.id, status: ticket!.status };
    },
  ],
  [
    "POST",
    /^\/tickets\/([^/]+)\/reject$/,
    ({ config, path }) => {
      requirePm(config);
      const ticket = store.tickets.find((candidate) => candidate.id === path[0]);
      if (!ticket) fail(404, "NOT_FOUND", "Ticket not found.");

      if (ticket!.status !== "PENDING_APPROVAL") {
        fail(
          409,
          "TICKET_NOT_AWAITING_APPROVAL",
          `Ticket is not awaiting approval (status: ${ticket!.status}).`,
        );
      }

      ticket!.status = "CANCELLED";
      ticket!.updated_at = nowIso();
      return { id: ticket!.id, status: ticket!.status };
    },
  ],
];

// ─── Adapter ─────────────────────────────────────────────────────────────────

function respond(
  config: InternalAxiosRequestConfig,
  status: number,
  data: unknown,
): AxiosResponse {
  return {
    data,
    status,
    statusText: String(status),
    headers: {},
    config,
    request: {},
  } as AxiosResponse;
}

export const demoAdapter: AxiosAdapter = async (config) => {
  await new Promise((resolve) => setTimeout(resolve, LATENCY_MS));

  const method = (config.method ?? "get").toUpperCase();
  const path = (config.url ?? "").split("?")[0];
  const params = (config.params ?? {}) as Record<string, string>;

  const route = routes.find(
    ([routeMethod, pattern]) => routeMethod === method && pattern.test(path),
  );

  if (!route) {
    throw new AxiosError(
      "Not found",
      "ERR_BAD_REQUEST",
      config,
      {},
      respond(config, 404, { error: "Not found.", code: "NOT_FOUND" }),
    );
  }

  const match = path.match(route[1])!;

  try {
    const data = route[2]({
      config,
      body: readBody(config),
      params,
      path: match.slice(1),
    });

    const status = method === "DELETE" ? 204 : method === "POST" ? 201 : 200;
    return respond(config, status, data ?? null);
  } catch (error) {
    if (error instanceof DemoFailure) {
      throw new AxiosError(
        error.message,
        "ERR_BAD_REQUEST",
        config,
        {},
        respond(config, error.status, { error: error.message, code: error.code }),
      );
    }
    throw error;
  }
};
