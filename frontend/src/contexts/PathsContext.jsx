import { createContext, useCallback, useContext, useMemo, useRef, useState } from "react";
import { useAuth } from "../hooks/useAuth";
import { newId, readJson, STORAGE_KEYS, writeJson } from "../services/localStore";
import { sanitizeAuditLog, sanitizePaths } from "../services/sanitize";
import { generateContent } from "../services/pipelineService";
import { approvalRule, can, validReason } from "../utils/pathWorkflow";
import { MIN_REASON_LENGTH } from "../utils/pathChecks";

// Kho lộ trình + audit log. Mọi thao tác kiểm tra quyền theo vai trò và trạng thái (utils/pathWorkflow),
// rồi ghi lộ trình và dòng audit trong cùng một lần lưu. Audit log chỉ thêm, không sửa, không xoá.
// Khi có backend: thay localStorage bằng /paths và /audit-logs, giữ nguyên chữ ký hàm.

const PathsContext = createContext(null);

export class PathError extends Error {
  constructor(key, vars) {
    super(key);
    this.key = key;
    this.vars = vars;
  }
}

const TITLES = {
  onboarding: ["Hội nhập", "Onboarding"],
  promotion: ["Bồi dưỡng thăng chức", "Promotion upskilling"],
};

export function PathsProvider({ children }) {
  const { user } = useAuth();
  const [paths, setPaths] = useState(() => sanitizePaths(readJson(STORAGE_KEYS.paths, [])));
  const [auditLog, setAuditLog] = useState(() => sanitizeAuditLog(readJson(STORAGE_KEYS.auditLog, [])));
  // Bản mới nhất để các thao tác async (sinh nội dung) không ghi đè thay đổi xảy ra trong lúc chờ
  const latest = useRef({ paths, auditLog });
  latest.current = { paths, auditLog };

  const actor = useMemo(() => (user ? { id: user.id, name: user.name, role: user.userRole } : null), [user]);

  const commit = useCallback((nextPaths, entry) => {
    if (!actor) throw new PathError("err_login_required");
    const prevLog = latest.current.auditLog;
    const nextLog = entry
      ? [{ id: newId("LOG"), timestamp: new Date().toISOString(), actor_id: actor.id, actor_name: actor.name, actor_role: actor.role, ...entry }, ...prevLog]
      : prevLog;
    if (!writeJson(STORAGE_KEYS.paths, nextPaths)) throw new PathError("err_storage_write");
    if (entry && !writeJson(STORAGE_KEYS.auditLog, nextLog)) {
      writeJson(STORAGE_KEYS.paths, latest.current.paths);
      throw new PathError("err_storage_write");
    }
    latest.current = { paths: nextPaths, auditLog: nextLog };
    setPaths(nextPaths);
    setAuditLog(nextLog);
  }, [actor]);

  const get = (id) => {
    const p = latest.current.paths.find(x => x.id === id);
    if (!p) throw new PathError("err_path_not_found");
    return p;
  };

  const guard = (action, path) => {
    if (!actor) throw new PathError("err_login_required");
    if (!can(actor.role, action, path)) throw new PathError("err_action_not_allowed");
  };

  const replace = (updated) => latest.current.paths.map(p => (p.id === updated.id ? updated : p));

  const logBase = (p) => ({ path_id: p.id, path_title: p.titleEn, revision: p.revision });

  const createPath = useCallback(async ({ role, level, purpose, sourceDocs, processed, prompt }) => {
    if (actor?.role !== "hr") throw new PathError("err_action_not_allowed");
    const id = newId("LP");
    const content = await generateContent({ id, role, level, purpose, sourceDocs, processed, prompt });
    const now = new Date().toISOString();
    const [vi, en] = TITLES[purpose] || TITLES.onboarding;
    const path = {
      id,
      title: `${vi} — ${role.name}`,
      titleEn: `${en} — ${role.nameEn}`,
      purpose, level,
      target: { role_id: role.id, department: role.department },
      sources: sourceDocs.map(d => ({ id: d.id, code: d.code, version: d.version, title: d.title, titleEn: d.titleEn })),
      prompt,
      ...content,
      status: "draft",
      revision: 1,
      comments: [],
      approval: null,
      published_to: null,
      created_by: actor,
      created_at: now,
      updated_at: now,
    };
    commit([path, ...latest.current.paths], { ...logBase(path), action: "generate", status_before: null, status_after: "draft", details: { engine: content.engine, sources: path.sources.map(s => s.code).join(", ") } });
    return path;
  }, [actor, commit]);

  const regeneratePath = useCallback(async (id, { role, sourceDocs, processed, prompt }) => {
    const path = get(id);
    guard("regenerate", path);
    const content = await generateContent({ id, role, level: path.level, purpose: path.purpose, sourceDocs, processed, prompt: prompt ?? path.prompt });
    const current = get(id);
    const updated = {
      ...current,
      ...content,
      sources: sourceDocs.map(d => ({ id: d.id, code: d.code, version: d.version, title: d.title, titleEn: d.titleEn })),
      prompt: prompt ?? current.prompt,
      updated_at: new Date().toISOString(),
    };
    commit(replace(updated), { ...logBase(updated), action: "regenerate", status_before: current.status, status_after: current.status, details: { engine: content.engine } });
  }, [commit]);

  /** @param {(path) => path} mutate  trả về bản lộ trình đã sửa; details mô tả thay đổi cho audit */
  const editPath = useCallback((id, mutate, details) => {
    const path = get(id);
    guard("edit", path);
    const updated = { ...mutate(path), updated_at: new Date().toISOString() };
    commit(replace(updated), { ...logBase(path), action: "edit", status_before: path.status, status_after: path.status, details });
  }, [commit]);

  const submitPath = useCallback((id, { note, finalStatus }) => {
    const path = get(id);
    guard("submit", path);
    const resubmit = path.status === "changes_requested";
    const updated = { ...path, status: "in_review", revision: resubmit ? path.revision + 1 : path.revision, submitted_at: new Date().toISOString() };
    const comments = note?.trim() ? [...path.comments, newComment(actor, note.trim(), null)] : path.comments;
    commit(replace({ ...updated, comments }), { ...logBase(updated), action: resubmit ? "resubmit" : "submit", status_before: path.status, status_after: "in_review", final_status: finalStatus, reason: note?.trim() || null });
  }, [actor, commit]);

  const requestChanges = useCallback((id, { message, finalStatus }) => {
    const path = get(id);
    guard("request_changes", path);
    if (!validReason(message)) throw new PathError("err_reason_required", { n: MIN_REASON_LENGTH });
    const updated = { ...path, status: "changes_requested", comments: [...path.comments, newComment(actor, message.trim(), null)] };
    commit(replace(updated), { ...logBase(path), action: "request_changes", status_before: path.status, status_after: "changes_requested", final_status: finalStatus, reason: message.trim() });
  }, [actor, commit]);

  const approvePath = useCallback((id, { departments, roles, reason, checks }) => {
    const path = get(id);
    guard("approve", path);
    const rule = approvalRule(checks);
    if (!rule.allowed) throw new PathError("err_approve_blocked");
    if (rule.reasonRequired && !validReason(reason)) throw new PathError("err_reason_required", { n: MIN_REASON_LENGTH });
    if (!departments.length && !roles.length) throw new PathError("err_publish_target");
    const now = new Date().toISOString();
    const updated = {
      ...path,
      status: "published",
      published_to: { departments, roles },
      approval: { by: actor, at: now, final_status: checks.final_status, reason: reason?.trim() || null },
      published_at: now,
    };
    commit(replace(updated), {
      ...logBase(path), action: "approve", status_before: path.status, status_after: "published", final_status: checks.final_status,
      reason: reason?.trim() || null, details: { departments: departments.join(", "), roles: roles.join(", ") },
    });
  }, [actor, commit]);

  const archivePath = useCallback((id, reason) => {
    const path = get(id);
    guard("archive", path);
    if (!validReason(reason)) throw new PathError("err_reason_required", { n: MIN_REASON_LENGTH });
    commit(replace({ ...path, status: "archived", archived_at: new Date().toISOString() }), { ...logBase(path), action: "archive", status_before: path.status, status_after: "archived", reason: reason.trim() });
  }, [commit]);

  const deletePath = useCallback((id) => {
    const path = get(id);
    guard("delete", path);
    commit(latest.current.paths.filter(p => p.id !== id), { ...logBase(path), action: "delete", status_before: path.status, status_after: null });
  }, [commit]);

  const addComment = useCallback((id, { text, itemRef = null, replyTo = null }) => {
    const path = get(id);
    guard("comment", path);
    if (!text?.trim()) throw new PathError("err_comment_empty");
    const comment = { ...newComment(actor, text.trim(), itemRef), reply_to: replyTo };
    commit(replace({ ...path, comments: [...path.comments, comment] }), { ...logBase(path), action: "comment", status_before: path.status, status_after: path.status, reason: text.trim(), details: itemRef ? { item: itemRef.id } : undefined });
  }, [actor, commit]);

  const resolveComment = useCallback((id, commentId, resolved = true) => {
    const path = get(id);
    guard("comment", path);
    const comments = path.comments.map(c => (c.id === commentId ? { ...c, resolved, resolved_by: resolved ? actor : null } : c));
    commit(replace({ ...path, comments }), null);
  }, [actor, commit]);

  const value = useMemo(() => ({
    paths,
    auditLog,
    getPath: id => paths.find(p => p.id === id) || null,
    createPath, regeneratePath, editPath, submitPath, requestChanges, approvePath, archivePath, deletePath, addComment, resolveComment,
  }), [paths, auditLog, createPath, regeneratePath, editPath, submitPath, requestChanges, approvePath, archivePath, deletePath, addComment, resolveComment]);

  return <PathsContext.Provider value={value}>{children}</PathsContext.Provider>;
}

function newComment(actor, text, itemRef) {
  return { id: newId("CMT"), author: actor, at: new Date().toISOString(), text, item_ref: itemRef, reply_to: null, resolved: false, resolved_by: null };
}

export function usePaths() {
  const ctx = useContext(PathsContext);
  if (!ctx) throw new Error("usePaths must be used inside <PathsProvider>");
  return ctx;
}
