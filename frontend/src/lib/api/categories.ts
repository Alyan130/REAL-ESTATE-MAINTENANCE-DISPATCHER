import { apiClient } from "@/lib/api-client";
import type {
  CategorySetting,
  CreateCategoryRequest,
  UpdateCategoryRequest,
} from "@/lib/types";

/**
 * The PM's maintenance categories and their prices.
 *
 * `vendorSelectableOnly` drops "other", which is the intake fallback and never
 * a vendor's specialty — pass it wherever a vendor is being tagged.
 */
export async function listCategories(
  vendorSelectableOnly = false,
): Promise<CategorySetting[]> {
  const { data } = await apiClient.get<CategorySetting[]>("/categories/", {
    params: vendorSelectableOnly ? { vendor_selectable_only: true } : undefined,
  });
  return data;
}

/** 400 DUPLICATE_CATEGORY when the slug is already taken by an active category. */
export async function createCategory(
  body: CreateCategoryRequest,
): Promise<CategorySetting> {
  const { data } = await apiClient.post<CategorySetting>("/categories/", body);
  return data;
}

/**
 * Only the fields present in `body` are changed. Sending `max_price: null`
 * clears the ceiling, which turns auto-approval off for the category.
 */
export async function updateCategory(
  categoryId: string,
  body: UpdateCategoryRequest,
): Promise<CategorySetting> {
  const { data } = await apiClient.patch<CategorySetting>(
    `/categories/${categoryId}`,
    body,
  );
  return data;
}

/** Soft delete. 400 PROTECTED_CATEGORY for "other". */
export async function deleteCategory(categoryId: string): Promise<void> {
  await apiClient.delete(`/categories/${categoryId}`);
}
