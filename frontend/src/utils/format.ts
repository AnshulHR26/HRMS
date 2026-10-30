export function humanize(value: string | null | undefined): string {
  if (!value) return "—";
  return value
    .toLowerCase()
    .split("_")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}

export function formatDate(value: string | null | undefined): string {
  if (!value) return "—";
  // Plain dates (YYYY-MM-DD) are parsed as local dates to avoid timezone shifts.
  const date = /^\d{4}-\d{2}-\d{2}$/.test(value) ? new Date(`${value}T00:00:00`) : new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleDateString(undefined, { day: "2-digit", month: "short", year: "numeric" });
}

export function formatDateTime(value: string | null | undefined): string {
  if (!value) return "Never";
  const date = new Date(value);
  return date.toLocaleString(undefined, { day: "2-digit", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" });
}

export function tenure(joiningDate: string): string {
  const start = new Date(`${joiningDate}T00:00:00`);
  const now = new Date();
  let months = (now.getFullYear() - start.getFullYear()) * 12 + (now.getMonth() - start.getMonth());
  if (now.getDate() < start.getDate()) months -= 1;
  if (months < 0) return "Joining soon";
  const years = Math.floor(months / 12);
  const rest = months % 12;
  if (years === 0) return `${rest} month${rest === 1 ? "" : "s"}`;
  return `${years} yr${years === 1 ? "" : "s"}${rest ? ` ${rest} mo` : ""}`;
}
