import { apiClient } from "@/lib/api-client";
import type { CreateTenantRequest, Tenant } from "@/lib/types";

export async function listTenants(propertyId?: string): Promise<Tenant[]> {
  const { data } = await apiClient.get<Tenant[]>("/tenants/", {
    params: propertyId ? { property_id: propertyId } : undefined,
  });
  return data;
}

export async function getTenant(tenantId: string): Promise<Tenant> {
  const { data } = await apiClient.get<Tenant>(`/tenants/${tenantId}`);
  return data;
}

/** Creates the user + tenant profile and sends the invite email. */
export async function inviteTenant(body: CreateTenantRequest): Promise<Tenant> {
  const { data } = await apiClient.post<Tenant>("/auth/invites/tenants", body);
  return data;
}

/** Resending invalidates every earlier invite link for this tenant. */
export async function resendTenantInvite(tenantId: string): Promise<void> {
  await apiClient.post(`/auth/invites/tenants/${tenantId}/resend`);
}

/** Disables the tenant profile and their login together. There is no undo endpoint. */
export async function deactivateTenant(tenantId: string): Promise<void> {
  await apiClient.delete(`/tenants/${tenantId}`);
}
