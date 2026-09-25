// Dữ liệu trong localStorage / IndexedDB có thể do phiên bản cũ của app ghi, hoặc bị sửa tay.
// Bản ghi sai cấu trúc bị bỏ qua khi đọc để một bản ghi hỏng không làm trắng cả ứng dụng.
import { emptyEnrollment } from "../utils/progress";

const isObj = v => v !== null && typeof v === "object" && !Array.isArray(v);
const arr = v => (Array.isArray(v) ? v : []);

const PATH_STATUSES = new Set(["draft", "in_review", "changes_requested", "published", "archived"]);

function validModule(m) {
  return isObj(m) && typeof m.id === "string" && Array.isArray(m.lessons) && Array.isArray(m.tasks) && Array.isArray(m.quiz)
    && m.quiz.every(q => isObj(q) && Array.isArray(q.options));
}

function validPath(p) {
  return isObj(p) && typeof p.id === "string" && PATH_STATUSES.has(p.status)
    && isObj(p.target) && typeof p.target.role_id === "string"
    && Array.isArray(p.stages) && p.stages.every(s => isObj(s) && typeof s.key === "string" && Array.isArray(s.modules) && s.modules.every(validModule))
    && (p.status !== "published" || (isObj(p.published_to) && Array.isArray(p.published_to.departments) && Array.isArray(p.published_to.roles)));
}

export function sanitizePaths(value) {
  return arr(value).filter(validPath).map(p => ({ ...p, sources: arr(p.sources), comments: arr(p.comments).filter(isObj), excluded_chunks: arr(p.excluded_chunks) }));
}

export function sanitizeAuditLog(value) {
  return arr(value).filter(e => isObj(e) && typeof e.id === "string" && typeof e.action === "string");
}

/** { userId: { pathId: enrollment } } — mỗi enrollment được bù các field còn thiếu */
export function sanitizeEnrollments(value) {
  if (!isObj(value)) return {};
  const out = {};
  for (const [userId, byPath] of Object.entries(value)) {
    if (!isObj(byPath)) continue;
    out[userId] = {};
    for (const [pathId, e] of Object.entries(byPath)) {
      if (!isObj(e)) continue;
      out[userId][pathId] = {
        ...emptyEnrollment(),
        ...e,
        lessonsRead: arr(e.lessonsRead),
        tasksDone: arr(e.tasksDone),
        quiz: isObj(e.quiz) ? e.quiz : {},
      };
    }
  }
  return out;
}

export function sanitizeDocuments(value) {
  return arr(value).filter(d => isObj(d) && typeof d.id === "string" && typeof d.code === "string"
    && typeof d.version === "string" && typeof d.fileName === "string");
}
