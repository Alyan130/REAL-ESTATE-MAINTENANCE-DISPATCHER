import { apiClient } from "@/lib/api-client";
import type {
  CreateTicketRequest,
  StatusUpdateResponse,
  Ticket,
  TicketCreatedResponse,
  TicketFilters,
  TicketStatus,
} from "@/lib/types";

export async function listTickets(filters: TicketFilters = {}): Promise<Ticket[]> {
  const params: Record<string, string> = {};
  if (filters.property_id) params.property_id = filters.property_id;
  if (filters.ticket_status) params.ticket_status = filters.ticket_status;
  if (filters.category) params.category = filters.category;

  const { data } = await apiClient.get<Ticket[]>("/tickets", { params });
  return data;
}

export async function getTicket(ticketId: string): Promise<Ticket> {
  const { data } = await apiClient.get<Ticket>(`/tickets/${ticketId}`);
  return data;
}

/**
 * Submit a ticket. Multipart, because the route takes Form fields plus files.
 *
 * Returns as soon as the row is written — photo upload and AI classification run
 * in the background, so the ticket comes back with no category or summary yet.
 */
export async function createTicket(
  body: CreateTicketRequest,
): Promise<TicketCreatedResponse> {
  const form = new FormData();
  form.append("title", body.title);
  if (body.description) form.append("description", body.description);
  form.append("permission_to_enter", String(body.permission_to_enter));
  body.photos.forEach((photo) => form.append("photos", photo));

  const { data } = await apiClient.post<TicketCreatedResponse>("/tickets", form, {
    headers: { "Content-Type": "multipart/form-data" },
    // Uploads can be slow on a phone connection; the default 30s is too tight.
    timeout: 120_000,
  });
  return data;
}

/**
 * Approve a pending ticket. Asynchronous: this resolves with `DISPATCHING`
 * while vendor selection runs, and the ticket settles on `DISPATCHED` or
 * `NEEDS_ATTENTION` seconds later. There is no push channel — poll for the result.
 *
 * 409 if the ticket is not exactly `PENDING_APPROVAL`.
 */
export async function approveTicket(ticketId: string): Promise<StatusUpdateResponse> {
  const { data } = await apiClient.post<StatusUpdateResponse>(
    `/tickets/${ticketId}/approve`,
  );
  return data;
}

/** Immediate and terminal — the ticket becomes `CANCELLED` with no undo. */
export async function rejectTicket(ticketId: string): Promise<StatusUpdateResponse> {
  const { data } = await apiClient.post<StatusUpdateResponse>(
    `/tickets/${ticketId}/reject`,
  );
  return data;
}

/** Manual override. Advanced escape hatch for unsticking a NEEDS_ATTENTION ticket. */
export async function updateTicketStatus(
  ticketId: string,
  status: TicketStatus,
): Promise<StatusUpdateResponse> {
  const { data } = await apiClient.patch<StatusUpdateResponse>(
    `/tickets/${ticketId}/status`,
    { status },
  );
  return data;
}
