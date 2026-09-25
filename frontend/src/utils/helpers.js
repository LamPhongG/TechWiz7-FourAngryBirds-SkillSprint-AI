// Hiển thị ngày ISO ("2026-09-28") theo locale đang chọn ("vi-VN" / "en-US")
export function formatLocalDate(iso, locale = "en-US", options = { month: "short", day: "numeric" }) {
  if (!iso) return "";
  // Đọc theo nửa đêm giờ địa phương để ngày không bị lệch theo múi giờ
  const date = new Date(`${iso}T00:00:00`);
  return Number.isNaN(date.getTime()) ? iso : date.toLocaleDateString(locale, options);
}

// Ngày giờ đầy đủ theo múi giờ người xem, dùng cho nhật ký kiểm toán
export function formatDateTime(iso, locale = "en-US") {
  if (!iso) return "";
  const date = new Date(iso);
  return Number.isNaN(date.getTime())
    ? iso
    : date.toLocaleString(locale, { day: "2-digit", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" });
}

// Ngày hôm nay dạng ISO "YYYY-MM-DD" theo giờ địa phương
export function todayISO() {
  const d = new Date();
  const pad = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}
