import { apiClient } from "@/lib/api-client";
import type { CreatePropertyRequest, Property } from "@/lib/types";

/** Paths keep the backend's exact trailing slash so no request eats a 307 redirect. */

export async function listProperties(): Promise<Property[]> {
  const { data } = await apiClient.get<Property[]>("/properties/");
  return data;
}

export async function getProperty(propertyId: string): Promise<Property> {
  const { data } = await apiClient.get<Property>(`/properties/${propertyId}`);
  return data;
}

export async function createProperty(
  body: CreatePropertyRequest,
): Promise<Property> {
  const { data } = await apiClient.post<Property>("/properties/", body);
  return data;
}

/** Soft delete — the property leaves the list but its tickets and tenants survive. */
export async function deleteProperty(propertyId: string): Promise<void> {
  await apiClient.delete(`/properties/${propertyId}`);
}
