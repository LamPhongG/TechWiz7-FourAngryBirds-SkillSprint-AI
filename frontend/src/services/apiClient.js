// Connect to FastAPI backend. Set VITE_API_URL in frontend/.env.local (e.g. http://localhost:8000/api)
// to enable; if left blank, services fallback to browser-mode processing.

const API_BASE = (import.meta.env?.VITE_API_URL || "").replace(/\/+$/, "");

export function backendEnabled() {
  return API_BASE !== "";
}

// Login auth token managed by useAuth; automatically attached to Authorization header
let authToken = null;
let onUnauthorized = null;

export function setAuthToken(token) {
  authToken = token || null;
}

/** useAuth registers logout handler: on token expiry or account deactivation, redirect to login page */
export function setUnauthorizedHandler(handler) {
  onUnauthorized = handler;
}

class ApiError extends Error {
  /**
   * @param {string} message  English error message from backend (`detail`)
   * @param {number} status
   * @param {string|null} code  Frontend translation key (`err_...`) when provided by backend
   * @param {object} vars       Parameters for translation key
   */
  constructor(message, status, code = null, vars = {}) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.vars = vars || {};
  }
}

// FastAPI returns errors as { detail: "...", code?, vars? } or { detail: [{ msg }] } (Pydantic validation error)
function toApiError(body, status) {
  const detail = body?.detail;
  let message = `HTTP ${status}`;
  if (typeof detail === "string") message = detail;
  else if (Array.isArray(detail)) message = detail.map(d => d.msg).join("; ");
  return new ApiError(message, status, body?.code || null, body?.vars);
}

function authHeaders(headers = {}) {
  return authToken ? { ...headers, Authorization: `Bearer ${authToken}` } : headers;
}

function handleUnauthorized(status) {
  // 401 with existing token indicates session expiry; wrong credentials (no token) handled by Login page
  if (status === 401 && authToken) onUnauthorized?.();
}

export async function apiRequest(path, { method = "GET", body, headers = {}, query } = {}) {
  const isForm = body instanceof FormData;
  const qs = query ? `?${new URLSearchParams(Object.entries(query).filter(([, v]) => v != null))}` : "";
  let res;
  try {
    res = await fetch(`${API_BASE}${path}${qs}`, {
      method,
      headers: authHeaders(isForm || body == null ? headers : { "Content-Type": "application/json", ...headers }),
      body: isForm || body == null ? body : JSON.stringify(body),
    });
  } catch {
    throw new ApiError("Network error", 0, "err_network");
  }
  if (res.status === 204) return null;
  const data = await res.json().catch(() => null);
  if (!res.ok) {
    handleUnauthorized(res.status);
    throw toApiError(data, res.status);
  }
  return data;
}

/** Download file requiring authentication (cannot navigate directly as browser won't attach Authorization header) */
export async function apiBlob(path) {
  let res;
  try {
    res = await fetch(`${API_BASE}${path}`, { headers: authHeaders() });
  } catch {
    throw new ApiError("Network error", 0, "err_network");
  }
  if (!res.ok) {
    handleUnauthorized(res.status);
    throw toApiError(await res.json().catch(() => null), res.status);
  }
  return res.blob();
}

/**
 * Multipart upload with progress callback (fetch does not support upload progress so XHR is used).
 * @param {(ratio: number) => void} onProgress  0 → 1 according to bytes sent
 */
export function uploadWithProgress(path, formData, onProgress) {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", `${API_BASE}${path}`);
    if (authToken) xhr.setRequestHeader("Authorization", `Bearer ${authToken}`);
    xhr.responseType = "json";
    xhr.upload.onprogress = (e) => { if (e.lengthComputable) onProgress?.(e.loaded / e.total); };
    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) resolve(xhr.response);
      else {
        handleUnauthorized(xhr.status);
        reject(toApiError(xhr.response, xhr.status));
      }
    };
    xhr.onerror = () => reject(new ApiError("Network error", 0, "err_network"));
    xhr.send(formData);
  });
}
