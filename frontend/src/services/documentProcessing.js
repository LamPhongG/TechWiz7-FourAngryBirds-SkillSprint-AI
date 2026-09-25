// Xử lý tài liệu (WBS Phase 2): trích xuất → chia chunk → sàng lọc prompt injection.
// Có backend: gửi file tới POST /upload, backend trả chunk list + injection_flags.
// Chưa có backend: làm toàn bộ trong trình duyệt với cùng định dạng kết quả.
import { backendEnabled, uploadWithProgress } from "./apiClient";
import { extractText } from "./textExtraction";
import { chunkBlocks, chunkCsv } from "../utils/chunker";
import { scanChunks } from "../utils/injectionScan";

/**
 * @param {object} doc   metadata tài liệu (id, code, version, ext, fileName)
 * @param {Blob}   blob  nội dung file
 * @param {(p: {percent: number, stage: string}) => void} onProgress
 * @returns {Promise<{engine, chunks, injection_flags, page_count, char_count, processed_at}>}
 */
export async function processDocument(doc, blob, onProgress = () => {}) {
  return backendEnabled() ? processOnBackend(doc, blob, onProgress) : processLocally(doc, blob, onProgress);
}

async function processOnBackend(doc, blob, onProgress) {
  const form = new FormData();
  form.append("file", blob, doc.fileName);
  form.append("doc_id", doc.code);
  form.append("version", doc.version);
  onProgress({ percent: 0, stage: "upload" });
  const res = await uploadWithProgress("/upload", form, ratio => onProgress({ percent: Math.round(ratio * 70), stage: "upload" }));
  onProgress({ percent: 85, stage: "chunk" });
  const chunks = Array.isArray(res) ? res : res?.chunks;
  if (!Array.isArray(chunks)) throw new Error("Backend response has no chunk list");
  // Backend chưa trả cờ injection thì vẫn sàng lọc phía trình duyệt để không bỏ sót cảnh báo
  const flags = Array.isArray(res?.injection_flags) ? res.injection_flags : scanChunks(chunks);
  onProgress({ percent: 100, stage: "done" });
  return {
    engine: "backend",
    chunks,
    injection_flags: flags,
    page_count: res?.page_count ?? null,
    char_count: chunks.reduce((n, c) => n + (c.content?.length || 0), 0),
    processed_at: new Date().toISOString(),
  };
}

async function processLocally(doc, blob, onProgress) {
  onProgress({ percent: 5, stage: "extract" });
  const { blocks, pageCount, raw } = await extractText(blob, doc.ext, ratio => onProgress({ percent: 5 + Math.round(ratio * 70), stage: "extract" }));
  onProgress({ percent: 80, stage: "chunk" });
  const chunks = doc.ext === "csv" ? chunkCsv(doc.code, raw) : chunkBlocks(doc.code, blocks);
  if (chunks.length === 0) {
    // PDF scan (chỉ có ảnh) không có lớp text — báo rõ thay vì trả về kho rỗng
    throw new Error(doc.ext === "pdf" ? "NO_TEXT_LAYER" : "NO_TEXT");
  }
  onProgress({ percent: 92, stage: "scan" });
  const flags = scanChunks(chunks);
  onProgress({ percent: 100, stage: "done" });
  return {
    engine: "browser",
    chunks,
    injection_flags: flags,
    page_count: pageCount,
    char_count: chunks.reduce((n, c) => n + c.content.length, 0),
    processed_at: new Date().toISOString(),
  };
}
