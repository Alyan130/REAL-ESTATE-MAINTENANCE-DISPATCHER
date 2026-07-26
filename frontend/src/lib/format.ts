/**
 * Date helpers.
 *
 * The API serialises naive UTC datetimes (no trailing `Z`), which browsers would
 * otherwise read as local time and render hours off. `parseApiDate` normalises
 * that before anything is displayed.
 */
function parseApiDate(value: string): Date {
  const hasTimezone = /(?:Z|[+-]\d{2}:?\d{2})$/.test(value);
  const hasTime = value.includes("T");
  return new Date(hasTime && !hasTimezone ? `${value}Z` : value);
}

export function formatDate(value: string | null | undefined): string {
  if (!value) return "—";
  const date = parseApiDate(value);
  if (Number.isNaN(date.getTime())) return "—";

  return date.toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

export function formatDateTime(value: string | null | undefined): string {
  if (!value) return "—";
  const date = parseApiDate(value);
  if (Number.isNaN(date.getTime())) return "—";

  return date.toLocaleString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

export function formatRelative(value: string | null | undefined): string {
  if (!value) return "—";
  const date = parseApiDate(value);
  if (Number.isNaN(date.getTime())) return "—";

  const seconds = Math.round((Date.now() - date.getTime()) / 1000);
  if (seconds < 60) return "just now";

  const minutes = Math.round(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;

  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours}h ago`;

  const days = Math.round(hours / 24);
  if (days < 7) return `${days}d ago`;

  return formatDate(value);
}

/** Short id for display next to a ticket, e.g. `a1b2c3d4`. */
export function shortId(id: string): string {
  return id.split("-")[0] ?? id;
}
