// Kiểm tra tài liệu tải lên (SRS Step 5) và vòng đời phiên bản (SRS Step 8)
// Mọi lỗi/cảnh báo trả về dạng { key, vars } để giao diện dịch bằng t()
import { DOCUMENT_CATALOG, UPLOAD_RULES } from "../data/company";

const CODE_PATTERN = /^DOC-\d{2,}$/;
const VERSION_PATTERN = /^\d+(\.\d+){0,2}$/;

function getExtension(fileName = "") {
  const dot = fileName.lastIndexOf(".");
  return dot === -1 ? "" : fileName.slice(dot + 1).toLowerCase();
}

export function normalizeVersion(value = "") {
  return String(value).trim().replace(/^v/i, "");
}

// So sánh "2.0" với "1.10": trả về >0, 0, <0
export function compareVersions(a, b) {
  const pa = normalizeVersion(a).split(".").map(Number);
  const pb = normalizeVersion(b).split(".").map(Number);
  for (let i = 0; i < Math.max(pa.length, pb.length); i++) {
    const diff = (pa[i] || 0) - (pb[i] || 0);
    if (diff !== 0) return diff;
  }
  return 0;
}

export function findCatalogEntry(code) {
  return DOCUMENT_CATALOG.find(entry => entry.code === String(code).trim().toUpperCase());
}

function slugify(text = "") {
  return text
    .toLowerCase()
    .replace(/\bobsolete\b/g, "")
    .normalize("NFD").replace(/[̀-ͯ]/g, "")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "");
}

// Nhóm phiên bản: theo danh mục nếu mã có trong danh mục, không thì theo tên tài liệu
export function familyOf({ code, titleEn }) {
  return findCatalogEntry(code)?.family || slugify(titleEn);
}

// "DOC-01_Employee_Handbook_v2.0.docx" → { code: "DOC-01", version: "2.0", titleEn: "Employee Handbook", obsoleteHint: false }
function parseFileName(fileName) {
  const base = fileName.replace(/\.[^.]+$/, "");
  const code = base.match(/^(DOC-\d{2,})/i)?.[1]?.toUpperCase() || "";
  const version = base.match(/[_\s-]v(\d+(?:\.\d+){0,2})/i)?.[1] || "";
  const obsoleteHint = /obsolete/i.test(base);
  const titleEn = base
    .replace(/^DOC-\d{2,}[_\s-]*/i, "")
    .replace(/[_\s-]v\d+(?:\.\d+){0,2}/i, "")
    .replace(/[_\s-]*obsolete/i, "")
    .replace(/[_]+/g, " ")
    .trim();
  return { code, version, titleEn, obsoleteHint };
}

// Mã băm SHA-256 để phát hiện file trùng nội dung
export async function hashFile(file) {
  const buffer = await file.arrayBuffer();
  if (globalThis.crypto?.subtle) {
    const digest = await crypto.subtle.digest("SHA-256", buffer);
    return Array.from(new Uint8Array(digest)).map(b => b.toString(16).padStart(2, "0")).join("");
  }
  // crypto.subtle chỉ có trên HTTPS/localhost — dự phòng bằng FNV-1a (kém chắc chắn hơn nhưng vẫn phát hiện được trùng lặp)
  let hash = 0x811c9dc5;
  const bytes = new Uint8Array(buffer);
  for (let i = 0; i < bytes.length; i++) {
    hash ^= bytes[i];
    hash = Math.imul(hash, 0x01000193) >>> 0;
  }
  return `fnv-${hash.toString(16)}-${bytes.length}`;
}

// Kiểm tra nội dung thật của file: đúng định dạng, không rỗng
export async function inspectContent(file, ext) {
  const issues = [];
  if (file.size === 0) return [{ key: "err_file_empty" }];
  const head = new Uint8Array(await file.slice(0, 5).arrayBuffer());
  const headText = String.fromCharCode(...head);
  if (ext === "pdf" && !headText.startsWith("%PDF")) issues.push({ key: "err_file_corrupt", vars: { ext } });
  // DOCX là file ZIP → luôn bắt đầu bằng "PK\x03\x04"
  if (ext === "docx" && !(head[0] === 0x50 && head[1] === 0x4b && head[2] === 0x03 && head[3] === 0x04)) {
    issues.push({ key: "err_file_corrupt", vars: { ext } });
  }
  if (["txt", "md", "csv"].includes(ext)) {
    const text = await file.text();
    if (!text.trim()) issues.push({ key: "err_file_empty" });
  }
  return issues;
}

// Tạo bản nháp metadata từ tên file + danh mục công ty
export function buildDraft(file, { today }) {
  const ext = getExtension(file.name);
  const parsed = parseFileName(file.name);
  const catalog = findCatalogEntry(parsed.code);
  return {
    key: `${file.name}-${file.size}-${file.lastModified}-${Math.random().toString(36).slice(2, 8)}`,
    file,
    ext,
    hash: null,          // điền sau khi băm xong
    contentIssues: null, // điền sau khi đọc nội dung
    code: parsed.code,
    titleEn: catalog?.titleEn.replace(/\s*\(obsolete\)$/i, "") || parsed.titleEn,
    category: catalog?.category || "",
    department: catalog?.department || "",
    version: parsed.version || "1.0",
    effectiveDate: today,
    expiryDate: "",
    obsoleteHint: parsed.obsoleteHint,
  };
}

// Kiểm tra một bản nháp so với kho hiện có và các file khác trong cùng lượt tải
export function validateDraft(draft, { existing, batch, today }) {
  const errors = [];
  const warnings = [];
  const { allowedExtensions, maxSizeMB } = UPLOAD_RULES;
  const code = draft.code.trim().toUpperCase();
  const version = normalizeVersion(draft.version);
  const family = familyOf({ code, titleEn: draft.titleEn });

  if (!allowedExtensions.includes(draft.ext)) {
    errors.push({ key: "err_file_type", vars: { ext: draft.ext || "?", list: allowedExtensions.map(e => `.${e}`).join(", ") } });
  }
  if (draft.file.size > maxSizeMB * 1024 * 1024) errors.push({ key: "err_file_too_large", vars: { max: maxSizeMB } });
  if (draft.contentIssues) errors.push(...draft.contentIssues);

  if (draft.hash) {
    const same = existing.find(d => d.hash === draft.hash);
    if (same) errors.push({ key: "err_duplicate_file", vars: { code: same.code, version: same.version } });
    else if (batch.some(o => o.key !== draft.key && o.hash === draft.hash && batch.indexOf(o) < batch.indexOf(draft))) {
      errors.push({ key: "err_duplicate_in_batch" });
    }
  }

  if (!CODE_PATTERN.test(code)) errors.push({ key: "err_code_format" });
  if (!draft.titleEn.trim()) errors.push({ key: "err_title_required" });
  if (!draft.category) errors.push({ key: "err_category_required" });
  if (!draft.department) errors.push({ key: "err_department_required" });
  if (!VERSION_PATTERN.test(version)) errors.push({ key: "err_version_format" });
  if (!draft.effectiveDate) errors.push({ key: "err_effective_required" });
  if (draft.expiryDate && draft.effectiveDate && draft.expiryDate <= draft.effectiveDate) errors.push({ key: "err_expiry_before" });

  // Mã tài liệu đã thuộc về tài liệu khác
  const codeOwner = existing.find(d => d.code === code && d.family !== family);
  if (CODE_PATTERN.test(code) && codeOwner) errors.push({ key: "err_code_family", vars: { code, title: codeOwner.titleEn } });

  if (VERSION_PATTERN.test(version)) {
    const sameFamily = existing.filter(d => d.family === family);
    if (sameFamily.some(d => compareVersions(d.version, version) === 0)) {
      errors.push({ key: "err_version_exists", vars: { version } });
    } else {
      const newest = sameFamily.reduce((max, d) => (!max || compareVersions(d.version, max.version) > 0 ? d : max), null);
      if (newest && compareVersions(version, newest.version) < 0) warnings.push({ key: "warn_older_version", vars: { version: newest.version } });
      if (newest && compareVersions(version, newest.version) > 0) warnings.push({ key: "warn_newer_version", vars: { version: newest.version } });
    }
    const batchTwin = batch.find(o => o.key !== draft.key && familyOf({ code: o.code.trim().toUpperCase(), titleEn: o.titleEn }) === family
      && compareVersions(o.version, version) === 0 && batch.indexOf(o) < batch.indexOf(draft));
    if (batchTwin) errors.push({ key: "err_version_in_batch" });
  }

  if (draft.effectiveDate > today) warnings.push({ key: "warn_future_effective" });
  if (draft.expiryDate && draft.expiryDate < today) warnings.push({ key: "warn_expired" });
  if (CODE_PATTERN.test(code) && !findCatalogEntry(code)) warnings.push({ key: "warn_not_in_catalog" });
  if (draft.obsoleteHint) warnings.push({ key: "warn_obsolete_name" });

  const pending = draft.hash === null || draft.contentIssues === null;
  return { errors, warnings, pending, valid: !pending && errors.length === 0 };
}

// Vòng đời từng tài liệu: active / obsolete (bị bản mới thay) / expired / upcoming
export function computeLifecycle(documents, today) {
  const result = {};
  const inForce = d => d.effectiveDate <= today && !(d.expiryDate && d.expiryDate < today);
  for (const doc of documents) {
    if (doc.expiryDate && doc.expiryDate < today) { result[doc.id] = { status: "expired" }; continue; }
    if (doc.effectiveDate > today) { result[doc.id] = { status: "upcoming" }; continue; }
    const newer = documents
      .filter(o => o.family === doc.family && o.id !== doc.id && inForce(o) && compareVersions(o.version, doc.version) > 0)
      .sort((a, b) => compareVersions(b.version, a.version))[0];
    result[doc.id] = newer ? { status: "obsolete", supersededBy: newer } : { status: "active" };
  }
  return result;
}

export function formatFileSize(bytes = 0) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}
