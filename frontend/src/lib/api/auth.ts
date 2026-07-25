import { apiClient } from "@/lib/api-client";
import type { AcceptInviteRequest, LoginRequest, TokenResponse } from "@/lib/types";

export async function login(body: LoginRequest): Promise<TokenResponse> {
  const { data } = await apiClient.post<TokenResponse>("/auth/login", body);
  return data;
}

export async function acceptInvite(
  body: AcceptInviteRequest,
): Promise<TokenResponse> {
  const { data } = await apiClient.post<TokenResponse>("/auth/accept-invite", body);
  return data;
}
