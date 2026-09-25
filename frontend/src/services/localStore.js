// Đọc/ghi JSON vào localStorage cho dữ liệu nhỏ (lộ trình, audit log, tiến độ học).
// Storage bị chặn (private mode) hoặc dữ liệu hỏng thì trả về giá trị mặc định thay vì làm crash app.

export const STORAGE_KEYS = {
  paths: "skillsprint.paths.v1",
  auditLog: "skillsprint.audit_log.v2",
  enrollments: "skillsprint.enrollments.v1",
};

export function readJson(key, fallback) {
  try {
    const raw = localStorage.getItem(key);
    if (raw == null) return fallback;
    const value = JSON.parse(raw);
    return value ?? fallback;
  } catch {
    return fallback;
  }
}

/** @returns {boolean} false khi không ghi được (hết quota, storage bị chặn) */
export function writeJson(key, value) {
  try {
    localStorage.setItem(key, JSON.stringify(value));
    return true;
  } catch {
    return false;
  }
}

export function newId(prefix) {
  const rand = globalThis.crypto?.randomUUID?.().slice(0, 8) || Math.random().toString(36).slice(2, 10);
  return `${prefix}-${rand.toUpperCase()}`;
}
