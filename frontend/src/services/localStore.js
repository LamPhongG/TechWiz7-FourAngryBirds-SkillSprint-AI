// Read/write JSON to localStorage for lightweight data (paths, audit log, learning progress).
// If storage is blocked (e.g. private browsing) or corrupted, returns fallback rather than crashing the app.

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

/** @returns {boolean} false when writing fails (quota exceeded, storage blocked) */
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
