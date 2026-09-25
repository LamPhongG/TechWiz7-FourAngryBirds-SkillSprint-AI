// Kết nối backend FastAPI. Đặt VITE_API_URL trong frontend/.env.local (ví dụ http://localhost:8000)
// để bật; bỏ trống thì các service dùng chế độ xử lý trong trình duyệt.

const API_BASE = (import.meta.env?.VITE_API_URL || "").replace(/\/+$/, "");

export function backendEnabled() {
  return API_BASE !== "";
}

class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

// FastAPI trả lỗi dạng { detail: "..." } hoặc { detail: [{ msg }] } (lỗi validate Pydantic)
function errorMessage(body, status) {
  const detail = body?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) return detail.map(d => d.msg).join("; ");
  return `HTTP ${status}`;
}

export async function apiRequest(path, { method = "GET", body, headers = {} } = {}) {
  const isForm = body instanceof FormData;
  const res = await fetch(`${API_BASE}${path}`, {
    method,
    headers: isForm || body == null ? headers : { "Content-Type": "application/json", ...headers },
    body: isForm || body == null ? body : JSON.stringify(body),
  });
  const data = await res.json().catch(() => null);
  if (!res.ok) throw new ApiError(errorMessage(data, res.status), res.status);
  return data;
}

/**
 * Upload multipart có báo tiến độ (fetch chưa hỗ trợ upload progress nên dùng XHR).
 * @param {(ratio: number) => void} onProgress  0 → 1 theo số byte đã gửi
 */
export function uploadWithProgress(path, formData, onProgress) {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", `${API_BASE}${path}`);
    xhr.responseType = "json";
    xhr.upload.onprogress = (e) => { if (e.lengthComputable) onProgress?.(e.loaded / e.total); };
    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) resolve(xhr.response);
      else reject(new ApiError(errorMessage(xhr.response, xhr.status), xhr.status));
    };
    xhr.onerror = () => reject(new ApiError("Network error", 0));
    xhr.send(formData);
  });
}
