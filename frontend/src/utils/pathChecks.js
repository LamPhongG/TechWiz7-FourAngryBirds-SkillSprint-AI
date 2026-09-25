// Kiểm định lộ trình (luồng Ground Truth) — thuần JavaScript, không gọi AI.
// Ba câu hỏi Reviewer cần trả lời, mỗi câu một nhóm kiểm tra:
//   1. Đúng kiến thức? → mỗi bài học / nhiệm vụ / câu hỏi phải trích được nguyên văn từ tài liệu gốc
//   2. Đúng luồng?     → thứ tự giai đoạn, nền tảng trước nghiệp vụ, học phần có bài học và bài kiểm tra
//   3. Đúng chức năng? → Coverage Score theo Role Requirement Matrix — do Pipeline 2 (Python backend)
//      tính và trả về trong path.coverage; frontend chỉ hiển thị, không tự tính
// Cộng thêm sàng lọc prompt injection trên nội dung sẽ đến tay nhân viên.
import { STAGE_TEMPLATES } from "../data/company";
import { findQuoteInChunks, normalizeForMatch } from "./chunker";
import { scanChunks } from "./injectionScan";

export const COVERAGE_THRESHOLDS = { manualBelow: 0.6, warningBelow: 0.85 };
export const MIN_REASON_LENGTH = 10;

const CRITICAL_KNOWLEDGE = new Set(["hallucination", "contradiction", "source_missing"]);
const WARNING_KNOWLEDGE = new Set(["outdated_source", "pending"]);

function findDoc(ref, documents) {
  if (!ref) return null;
  return documents.find(d => d.id === ref.doc_id)
    || documents.find(d => d.code === ref.doc && d.status === "active")
    || documents.find(d => d.code === ref.doc)
    || null;
}

/** Liệt kê mọi mục có nội dung kiến thức kèm trích dẫn của nó */
function knowledgeItems(path) {
  const items = [];
  for (const stage of path.stages || []) {
    for (const m of stage.modules) {
      for (const l of m.lessons) items.push({ id: l.id, module_id: m.id, stage: stage.key, kind: "lesson", item: l, source_reference: l.source_reference });
      for (const t of m.tasks) items.push({ id: t.id, module_id: m.id, stage: stage.key, kind: "task", item: t, source_reference: t.source_reference });
      for (const q of m.quiz) items.push({ id: q.id, module_id: m.id, stage: stage.key, kind: "quiz", item: q, source_reference: q.source_reference });
    }
  }
  return items;
}

/**
 * @returns {Array<{id, module_id, kind, item, source_reference, status, chunk, doc}>}
 *   status: verified | hallucination | contradiction | source_missing | outdated_source | pending
 */
export function checkKnowledge(path, { documents, chunksByDocId }) {
  return knowledgeItems(path).map(entry => {
    const ref = entry.source_reference;
    if (!ref?.exact_quote?.trim()) return { ...entry, status: "source_missing", chunk: null, doc: null };
    const doc = findDoc(ref, documents);
    if (!doc) return { ...entry, status: "source_missing", chunk: null, doc: null };
    const chunks = chunksByDocId[doc.id];
    if (!chunks?.length) return { ...entry, status: "pending", chunk: null, doc };
    const chunk = findQuoteInChunks(ref.exact_quote, chunks, ref.page);
    if (!chunk) return { ...entry, status: "hallucination", chunk: null, doc };
    // Đáp án đúng phải có trong câu trích — nếu không, câu hỏi đang chấm theo một điều tài liệu không nói
    if (entry.kind === "quiz") {
      const correct = entry.item.options?.[entry.item.answer];
      if (correct == null || !normalizeForMatch(ref.exact_quote).includes(normalizeForMatch(correct))) {
        return { ...entry, status: "contradiction", chunk, doc };
      }
    }
    if (doc.status !== "active") return { ...entry, status: "outdated_source", chunk, doc };
    return { ...entry, status: "verified", chunk, doc };
  });
}

/** @returns {Array<{severity: "error"|"warning", key: string, vars?: object, module_id?: string}>} */
export function checkFlow(path) {
  const issues = [];
  const template = STAGE_TEMPLATES[path.purpose] || STAGE_TEMPLATES.onboarding;
  const stages = path.stages || [];

  let lastIndex = -1;
  for (const s of stages) {
    const idx = template.indexOf(s.key);
    if (idx < 0) issues.push({ severity: "error", key: "flow_unknown_stage", vars: { stage: s.key } });
    else if (idx <= lastIndex) issues.push({ severity: "error", key: "flow_stage_order", vars: { stage: s.key } });
    lastIndex = Math.max(lastIndex, idx);
    if (s.modules.length === 0) issues.push({ severity: "warning", key: "flow_empty_stage", vars: { stage: s.key } });
  }

  const modules = stages.flatMap((s, si) => s.modules.map(m => ({ m, si })));
  if (modules.length === 0) issues.push({ severity: "error", key: "flow_no_modules" });

  const docSeen = new Map();
  for (const { m } of modules) {
    const title = m.titleEn || m.title;
    if (m.kind !== "assessment" && m.lessons.length === 0) issues.push({ severity: "error", key: "flow_module_empty", vars: { module: title }, module_id: m.id });
    if (m.kind !== "assessment" && m.quiz.length === 0) issues.push({ severity: "warning", key: "flow_no_quiz", vars: { module: title }, module_id: m.id });
    for (const q of m.quiz) {
      if (!Array.isArray(q.options) || q.options.length < 2 || q.answer == null || q.answer < 0 || q.answer >= q.options.length) {
        issues.push({ severity: "error", key: "flow_quiz_invalid", vars: { module: title }, module_id: m.id });
      }
    }
    if (m.doc_code) {
      if (docSeen.has(m.doc_code)) issues.push({ severity: "warning", key: "flow_duplicate_doc", vars: { doc: m.doc_code }, module_id: m.id });
      docSeen.set(m.doc_code, true);
    }
  }

  // Kiến thức nền tảng (sổ tay, chính sách toàn công ty) phải học trước nghiệp vụ phòng ban
  const firstSpecific = modules.find(x => x.m.kind !== "assessment" && x.m.tier >= 3);
  if (firstSpecific) {
    for (const { m, si } of modules) {
      if (m.kind !== "assessment" && m.tier <= 1 && si > firstSpecific.si) {
        issues.push({ severity: "warning", key: "flow_foundation_late", vars: { module: m.titleEn || m.title }, module_id: m.id });
      }
    }
  }

  const assessments = modules.filter(x => x.m.kind === "assessment");
  if (assessments.length === 0) issues.push({ severity: "warning", key: "flow_no_final_assessment" });
  else if (assessments.some(x => x.si !== stages.length - 1)) issues.push({ severity: "warning", key: "flow_assessment_not_last" });

  return issues;
}

/**
 * Kết quả "đúng chức năng" do backend trả về: { score, requiredDocs: [{ code, covered }], topics: [{ id, label, covered, matchedKeyword }] }.
 * Dữ liệu sai dạng coi như chưa có để không hiển thị điểm không đáng tin.
 */
function backendCoverage(path) {
  const c = path.coverage;
  if (!c || typeof c.score !== "number" || c.score < 0 || c.score > 1) return null;
  return { ...c, requiredDocs: Array.isArray(c.requiredDocs) ? c.requiredDocs : [], topics: Array.isArray(c.topics) ? c.topics : [] };
}

/** Nội dung sẽ hiển thị cho nhân viên không được chứa câu lệnh tấn công */
function checkInjection(path) {
  const pseudo = knowledgeItems(path).map(e => ({
    chunk_id: e.id,
    page: e.source_reference?.page ?? null,
    content: e.kind === "lesson" ? `${e.item.title}\n${e.item.content}` : e.kind === "task" ? e.item.title : [e.item.question, ...(e.item.options || [])].join("\n"),
  }));
  return scanChunks(pseudo);
}

/**
 * Chạy toàn bộ kiểm tra và phân loại trạng thái cuối.
 * @returns {{knowledge, flow, coverage, injection, final_status, reasons, blocking}}
 *   blocking = true khi còn lỗi không được phép phát hành (sai kiến thức, injection, lỗi cấu trúc)
 */
export function runPathChecks(path, { documents, chunksByDocId }) {
  const knowledge = checkKnowledge(path, { documents, chunksByDocId });
  const flow = checkFlow(path);
  const coverage = backendCoverage(path);
  const injection = checkInjection(path);

  const critical = knowledge.filter(k => CRITICAL_KNOWLEDGE.has(k.status)).length;
  const warnKnowledge = knowledge.filter(k => WARNING_KNOWLEDGE.has(k.status)).length;
  const flowErrors = flow.filter(f => f.severity === "error").length;
  const flowWarnings = flow.filter(f => f.severity === "warning").length;
  const score = coverage ? coverage.score : null;

  const blockingReasons = [];
  const manual = [];
  const warnings = [];
  if (critical) blockingReasons.push({ key: "reason_knowledge_critical", vars: { n: critical } });
  if (injection.length) blockingReasons.push({ key: "reason_injection_content", vars: { n: injection.length } });
  if (flowErrors) blockingReasons.push({ key: "reason_flow_errors", vars: { n: flowErrors } });
  // Chưa có kết quả từ backend: không chặn duyệt, nhưng không được coi là Verified
  if (score == null) warnings.push({ key: "reason_coverage_pending" });
  else if (score < COVERAGE_THRESHOLDS.manualBelow) manual.push({ key: "reason_low_coverage", vars: { score: Math.round(score * 100), min: COVERAGE_THRESHOLDS.manualBelow * 100 } });
  else if (score < COVERAGE_THRESHOLDS.warningBelow) warnings.push({ key: "reason_medium_coverage", vars: { score: Math.round(score * 100), min: COVERAGE_THRESHOLDS.warningBelow * 100 } });
  if (warnKnowledge) warnings.push({ key: "reason_knowledge_warning", vars: { n: warnKnowledge } });
  if (flowWarnings) warnings.push({ key: "reason_flow_warnings", vars: { n: flowWarnings } });
  if (path.excluded_chunks?.length) warnings.push({ key: "reason_excluded_chunks", vars: { n: path.excluded_chunks.length } });

  let final_status = "verified";
  let reasons = [{ key: "reason_all_verified" }];
  if (blockingReasons.length || manual.length) {
    final_status = "manual_review";
    reasons = [...blockingReasons, ...manual, ...warnings];
  } else if (warnings.length) {
    final_status = "verified_warning";
    reasons = warnings;
  }
  return { knowledge, flow, coverage, injection, final_status, reasons, blocking: blockingReasons.length > 0 };
}
