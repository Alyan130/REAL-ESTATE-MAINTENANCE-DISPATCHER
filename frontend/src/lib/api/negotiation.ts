import { apiClient } from "@/lib/api-client";
import type {
  MessageAccepted,
  Negotiation,
  NegotiationAction,
  VendorChat,
} from "@/lib/types";

/**
 * The vendor's negotiation thread, and the PM's decision on it.
 *
 * The two vendor-facing calls take the token in the **path**, not as a query
 * param: one `PUBLIC_AUTH_PATHS` entry then covers both, and the token never
 * lands in axios's param logging.
 */

/** 400 INVALID_TOKEN · 404 NOT_FOUND · 410 CHAT_LINK_EXPIRED | CHAT_CLOSED */
export async function getVendorChat(token: string): Promise<VendorChat> {
  const { data } = await apiClient.get<VendorChat>(
    `/vendor-chat/${encodeURIComponent(token)}`,
  );
  return data;
}

/**
 * 202 — stored immediately, answered in the background.
 *
 * 409 CHAT_READ_ONLY once the job is settled, 429 MESSAGE_TOO_FAST on a
 * double-submit.
 */
export async function postVendorMessage(
  token: string,
  body: string,
): Promise<MessageAccepted> {
  const { data } = await apiClient.post<MessageAccepted>(
    `/vendor-chat/${encodeURIComponent(token)}/messages`,
    { body },
  );
  return data;
}

/**
 * 404 NEGOTIATION_NOT_FOUND when nothing is in flight — expected, not an error.
 * Call sites load this separately from the ticket so that 404 can't blank the page.
 */
export async function getNegotiation(ticketId: string): Promise<Negotiation> {
  const { data } = await apiClient.get<Negotiation>(
    `/tickets/${ticketId}/negotiation`,
  );
  return data;
}

/**
 * Accept the quote, counter it once, or move on.
 *
 * 409 COUNTER_LIMIT_REACHED on a second counter, 409
 * NEGOTIATION_NOT_AWAITING_DECISION on a double-click.
 */
export async function decideNegotiation(
  ticketId: string,
  action: NegotiationAction,
  counterPrice?: number | null,
): Promise<{ vendor_job_id: string; action: string }> {
  const { data } = await apiClient.post(`/tickets/${ticketId}/negotiation/decision`, {
    action,
    counter_price: counterPrice ?? null,
  });
  return data;
}
