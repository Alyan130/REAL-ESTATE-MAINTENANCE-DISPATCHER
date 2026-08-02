"use client";

import { SlidersHorizontal } from "lucide-react";

import { Button } from "@/components/ui/button";
import { listCategories } from "@/lib/api/categories";
import { ACTIVE_STATUSES, categoryLabel, statusLabel } from "@/lib/status";
import { TICKET_CATEGORIES, type Property } from "@/lib/types";
import { useAsync } from "@/lib/use-async";

export interface TicketFilterValue {
  propertyId: string;
  status: string;
  category: string;
}

export const EMPTY_FILTERS: TicketFilterValue = {
  propertyId: "",
  status: "",
  category: "",
};

interface TicketFiltersProps {
  value: TicketFilterValue;
  properties: Property[];
  onChange: (value: TicketFilterValue) => void;
  /** Hidden when the list is already scoped to one property. */
  showPropertyFilter?: boolean;
}

const SELECT_CLASSES =
  "h-9 rounded-full border border-line-soft bg-surface px-3 py-1 text-xs font-semibold text-ink transition-colors focus:border-brand focus:outline-none cursor-pointer";

export function TicketFilters({
  value,
  properties,
  onChange,
  showPropertyFilter = true,
}: TicketFiltersProps) {
  const active =
    Boolean(value.propertyId) || Boolean(value.status) || Boolean(value.category);

  // The PM's own categories. Until the fetch lands, fall back to the seed list
  // so the dropdown is never momentarily empty.
  const categories = useAsync(() => listCategories(), []);
  const options =
    categories.data ??
    TICKET_CATEGORIES.map((name) => ({ name, label: categoryLabel(name) }));

  return (
    <div className="flex flex-wrap items-center gap-2">
      <span className="inline-flex items-center gap-1.5 text-xs font-semibold text-muted mr-1">
        <SlidersHorizontal size={14} className="text-brand" />
        Filter
      </span>

      {showPropertyFilter ? (
        <select
          aria-label="Filter by property"
          className={SELECT_CLASSES}
          value={value.propertyId}
          onChange={(event) => onChange({ ...value, propertyId: event.target.value })}
        >
          <option value="">All properties</option>
          {properties.map((property) => (
            <option key={property.id} value={property.id}>
              {property.name}
            </option>
          ))}
        </select>
      ) : null}

      <select
        aria-label="Filter by status"
        className={SELECT_CLASSES}
        value={value.status}
        onChange={(event) => onChange({ ...value, status: event.target.value })}
      >
        <option value="">All statuses</option>
        {ACTIVE_STATUSES.map((status) => (
          <option key={status} value={status}>
            {statusLabel(status)}
          </option>
        ))}
      </select>

      <select
        aria-label="Filter by category"
        className={SELECT_CLASSES}
        value={value.category}
        onChange={(event) => onChange({ ...value, category: event.target.value })}
      >
        <option value="">All categories</option>
        {options.map((category) => (
          <option key={category.name} value={category.name}>
            {category.label}
          </option>
        ))}
      </select>

      {active ? (
        <Button size="sm" variant="ghost" onClick={() => onChange(EMPTY_FILTERS)}>
          Clear
        </Button>
      ) : null}
    </div>
  );
}
