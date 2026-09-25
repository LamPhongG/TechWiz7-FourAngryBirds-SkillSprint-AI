// Sinh nội dung lộ trình.
// Có backend (VITE_API_URL): POST /paths/generate — Pipeline 1 Gemini sinh nội dung, Pipeline 2 Python tính Coverage theo
// Role Requirement Matrix; trả về { stages, excluded_chunks, coverage, model, prompt_version }.
// Chưa có backend: bản nháp dựng từ cấu trúc tài liệu (utils/pathGenerator.js), engine = "local-draft".
import { apiRequest, backendEnabled } from "./apiClient";
import { generatePathContent } from "../utils/pathGenerator";

export const PROMPT_VERSION = import.meta.env?.VITE_PROMPT_VERSION || "v1.0";

/**
 * @returns {Promise<{stages, excluded_chunks, coverage, engine, model, prompt_version}>}
 */
export async function generateContent({ id, role, level, purpose, sourceDocs, processed, prompt }) {
  if (backendEnabled()) {
    const res = await apiRequest("/paths/generate", {
      method: "POST",
      body: { path_id: id, role_id: role.id, level, purpose, doc_ids: sourceDocs.map(d => d.code), prompt, prompt_version: PROMPT_VERSION },
    });
    if (!Array.isArray(res?.stages)) throw new Error("Backend response has no stages");
    return { stages: res.stages, excluded_chunks: res.excluded_chunks || [], coverage: res.coverage ?? null, engine: "gemini", model: res.model || null, prompt_version: res.prompt_version || PROMPT_VERSION };
  }
  const chunksByDocId = Object.fromEntries(sourceDocs.map(d => [d.id, processed[d.id]?.chunks || []]));
  const flagsByDocId = Object.fromEntries(sourceDocs.map(d => [d.id, processed[d.id]?.injection_flags || []]));
  const content = generatePathContent({ id, level, purpose, docs: sourceDocs, chunksByDocId, flagsByDocId });
  return { ...content, coverage: null, engine: "local-draft", model: null, prompt_version: PROMPT_VERSION };
}
