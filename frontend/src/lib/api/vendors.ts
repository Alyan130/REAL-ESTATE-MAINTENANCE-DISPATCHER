import { apiClient } from "@/lib/api-client";
import type { CreateVendorRequest, Vendor } from "@/lib/types";

export async function listVendors(): Promise<Vendor[]> {
  const { data } = await apiClient.get<Vendor[]>("/vendors/");
  return data;
}

export async function getVendor(vendorId: string): Promise<Vendor> {
  const { data } = await apiClient.get<Vendor>(`/vendors/${vendorId}`);
  return data;
}

/** Adds the vendor to the pool the dispatch agent selects from. */
export async function inviteVendor(body: CreateVendorRequest): Promise<Vendor> {
  const { data } = await apiClient.post<Vendor>("/auth/invites/vendors", body);
  return data;
}

export async function resendVendorInvite(vendorId: string): Promise<void> {
  await apiClient.post(`/auth/invites/vendors/${vendorId}/resend`);
}

/** Removes the vendor from AI selection and disables their login. */
export async function deactivateVendor(vendorId: string): Promise<void> {
  await apiClient.delete(`/vendors/${vendorId}`);
}
