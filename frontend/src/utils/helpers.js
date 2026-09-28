// Format ISO date ("2026-09-28") according to locale ("en-US")
export function formatLocalDate(iso, locale = "en-US", options = { month: "short", day: "numeric" }) {
  if (!iso) return "";
  // Parse at local midnight to prevent timezone skew
  const date = new Date(`${iso}T00:00:00`);
  return Number.isNaN(date.getTime()) ? iso : date.toLocaleDateString(locale, options);
}

// Full date-time formatted in user's timezone for audit logs
export function formatDateTime(iso, locale = "en-US") {
  if (!iso) return "";
  const date = new Date(iso);
  return Number.isNaN(date.getTime())
    ? iso
    : date.toLocaleString(locale, { day: "2-digit", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" });
}

// Current date in ISO "YYYY-MM-DD" format in local time
export function todayISO() {
  const d = new Date();
  const pad = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

