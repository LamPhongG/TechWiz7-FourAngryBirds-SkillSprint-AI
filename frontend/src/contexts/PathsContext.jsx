import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";
import { useAuth } from "../hooks/useAuth";
import { newId, readJson, STORAGE_KEYS, writeJson } from "../services/localStore";
import { sanitizeAuditLog, sanitizePaths } from "../services/sanitize";
import { generateContent } from "../services/pipelineService";
import { DEFAULT_ONBOARDING_DAYS } from "../data/company";
import { approvalRule, can, validReason } from "../utils/pathWorkflow";
import { MIN_REASON_LENGTH } from "../utils/pathChecks";
import { apiRequest, backendEnabled } from "../services/apiClient";
import { mapAuditEntry, mapPath } from "../services/apiMappers";
import { useLanguage } from "./LanguageContext";

// Learning paths store + audit log, sharing identical function signatures across both modes:
// - Browser mode: localStorage; all operations enforce role and status permissions (utils/pathWorkflow),
//   then persist path and audit entry within a single atomic save. Audit log is append-only (no edit/delete).
// - Backend mode (VITE_API_URL): /paths and /audit-logs; server generates content (Gemini), enforces permissions and audit rules.

const PathsContext = createContext(null);

export class PathError extends Error {
  constructor(key, vars) {
    super(key);
    this.key = key;
    this.vars = vars;
  }
}

const TITLES = {
  onboarding: ["Onboarding", "Onboarding"],
  promotion: ["Promotion upskilling", "Promotion upskilling"],
};

// Build-time fixed mode, so provider always invokes the same hook
const usePathSource = backendEnabled() ? useBackendPaths : useBrowserPaths;

export function PathsProvider({ children }) {
  const source = usePathSource();
  const value = useMemo(() => ({
    ...source,
    getPath: id => source.paths.find(p => p.id === id) || null,
  }), [source]);
  return <PathsContext.Provider value={value}>{children}</PathsContext.Provider>;
}

function useBrowserPaths() {
  const { user } = useAuth();
  const [paths, setPaths] = useState(() => sanitizePaths(readJson(STORAGE_KEYS.paths, [])));
  const [auditLog, setAuditLog] = useState(() => sanitizeAuditLog(readJson(STORAGE_KEYS.auditLog, [])));
  // Latest ref prevents asynchronous operations (path generation) from overwriting concurrent changes
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

  const createPath = useCallback(async ({ role, level, purpose, durationDays, sourceDocs, processed, prompt }) => {
    if (actor?.role !== "hr") throw new PathError("err_action_not_allowed");
    const id = newId("LP");
    // Server-aligned: duration only applies to onboarding paths
    const duration = purpose === "onboarding" ? durationDays || DEFAULT_ONBOARDING_DAYS : null;
    const content = await generateContent({ id, role, level, purpose, durationDays: duration, sourceDocs, processed, prompt });
    const now = new Date().toISOString();
    const [, en] = TITLES[purpose] || TITLES.onboarding;
    const path = {
      id,
      title: `${en} — ${role.name}`,
      titleEn: `${en} — ${role.nameEn}`,
      purpose, level,
      duration_days: duration,
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
    const content = await generateContent({ id, role, level: path.level, purpose: path.purpose, durationDays: path.duration_days, sourceDocs, processed, prompt: prompt ?? path.prompt });
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

  /** @param {(path) => path} mutate  returns updated path object; details describes change for audit */
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

  // Browser mode reads synchronously from localStorage; no reload required
  const refreshPaths = useCallback(() => Promise.resolve(), []);

  return useMemo(() => ({
    paths,
    auditLog,
    createPath, regeneratePath, editPath, submitPath, requestChanges, approvePath, archivePath, deletePath, addComment, resolveComment, refreshPaths, loaded: true,
  }), [paths, auditLog, createPath, regeneratePath, editPath, submitPath, requestChanges, approvePath, archivePath, deletePath, addComment, resolveComment, refreshPaths]);
}

// Backend domain errors carry translation key (err_...) -> PathError for unified display across modes
const JOB_POLL_MS = 700;

function asPathError(e) {
  return e?.code ? new PathError(e.code, e.vars) : e;
}

function useBackendPaths() {
  const { user } = useAuth();
  const { lang } = useLanguage();
  const [paths, setPaths] = useState([]);
  const [auditLog, setAuditLog] = useState([]);
  // Initial load pending: employee page displays "loading" rather than empty state
  const [loaded, setLoaded] = useState(false);
  const latest = useRef(paths);
  latest.current = paths;
  // Admins read the audit trail too (SRS Step 49, 51); employees never do.
  const canReadAudit = ["hr", "reviewer", "admin"].includes(user?.userRole);

  const reloadAudit = useCallback(async () => {
    if (!canReadAudit) return;
    const page = await apiRequest("/audit-logs", { query: { limit: 1000 } });
    setAuditLog(page.items.map(mapAuditEntry));
  }, [canReadAudit]);

  useEffect(() => {
    if (!user) {
      setPaths([]);
      setAuditLog([]);
      setLoaded(false);
      return;
    }
    let cancelled = false;
    // Fetch full path with stages: list, progress tracking, and verification checks require stages
    apiRequest("/paths", { query: { include_content: true } })
      .then(list => { if (!cancelled) setPaths(list.map(mapPath)); })
      .catch(() => { if (!cancelled) setPaths([]); })
      .finally(() => { if (!cancelled) setLoaded(true); });
    reloadAudit().catch(() => {});
    return () => { cancelled = true; };
  }, [user, reloadAudit]);

  /** Invoke API, update path in local state list, reload audit log */
  const call = useCallback(async (path, options) => {
    let result;
    try {
      result = await apiRequest(path, options);
    } catch (e) {
      throw asPathError(e);
    }
    const updated = result ? mapPath(result) : null;
    if (updated) {
      setPaths(prev => (prev.some(p => p.id === updated.id) ? prev.map(p => (p.id === updated.id ? updated : p)) : [updated, ...prev]));
    }
    reloadAudit().catch(() => {});
    return updated;
  }, [reloadAudit]);

  /**
   * Background generation job: server returns job immediately, frontend polls every JOB_POLL_MS and tracks stages
   * (sources -> analysis -> outline -> modules -> coverage matrix -> save) via onProgress(job).
   */
  const runJob = useCallback(async (startPath, body, onProgress) => {
    let job;
    try {
      job = await apiRequest(startPath, { method: "POST", body });
      onProgress?.(job);
      while (job.status === "running") {
        await new Promise(resolve => setTimeout(resolve, JOB_POLL_MS));
        job = await apiRequest(`/paths/jobs/${job.id}`);
        onProgress?.(job);
      }
    } catch (e) {
      throw asPathError(e);
    }
    if (job.status === "failed") throw asPathError(job.error);
    return call(`/paths/${job.path_id}`);
  }, [call]);

  // allowMissingMandatory: HR opted to exclude mandatory documents; server still generates and flags Reviewer
  const createPath = useCallback(({ role, level, purpose, durationDays, sourceDocs, prompt, allowMissingMandatory, onProgress }) => runJob("/paths/jobs", {
    job_position_id: role.id, level, purpose, source_document_ids: sourceDocs.map(d => d.id), prompt, language: lang,
    duration_days: purpose === "onboarding" ? durationDays : null, allow_missing_mandatory: !!allowMissingMandatory,
  }, onProgress), [runJob, lang]);

  const regeneratePath = useCallback((id, { sourceDocs, prompt, allowMissingMandatory, onProgress }) => runJob(`/paths/${id}/regenerate/jobs`, {
    source_document_ids: sourceDocs.map(d => d.id), prompt, language: lang, allow_missing_mandatory: !!allowMissingMandatory,
  }, onProgress), [runJob, lang]);

  const editPath = useCallback((id, mutate, details) => {
    const path = latest.current.find(p => p.id === id);
    if (!path) return Promise.reject(new PathError("err_path_not_found"));
    const detailStrings = details ? Object.fromEntries(Object.entries(details).map(([k, v]) => [k, String(v)])) : null;
    return call(`/paths/${id}`, { method: "PATCH", body: { stages: mutate(path).stages, details: detailStrings } });
  }, [call]);

  const submitPath = useCallback((id, { note }) => call(`/paths/${id}/submit`, { method: "POST", body: { note } }), [call]);

  const requestChanges = useCallback((id, { message }) =>
    call(`/paths/${id}/request-changes`, { method: "POST", body: { message } }), [call]);

  // Server runs pre-publish verification check; client-side checks are for display
  const approvePath = useCallback((id, { departments, roles, reason }) =>
    call(`/paths/${id}/approve`, { method: "POST", body: { departments, job_positions: roles, reason } }), [call]);

  const archivePath = useCallback((id, reason) => call(`/paths/${id}/archive`, { method: "POST", body: { reason } }), [call]);

  const deletePath = useCallback(async (id) => {
    await call(`/paths/${id}`, { method: "DELETE" });
    setPaths(prev => prev.filter(p => p.id !== id));
  }, [call]);

  const addComment = useCallback((id, { text, itemRef = null, replyTo = null }) => call(`/paths/${id}/comments`, {
    method: "POST",
    body: { text, item_ref: itemRef ? { id: itemRef.id, label: itemRef.label ?? null } : null, reply_to: replyTo },
  }), [call]);

  const resolveComment = useCallback((id, commentId, resolved = true) =>
    call(`/paths/${id}/comments/${commentId}/resolve`, { method: "POST", body: { resolved } }), [call]);

  // Self-enrolling in a path makes it visible: refresh list
  const refreshPaths = useCallback(async () => {
    const list = await apiRequest("/paths", { query: { include_content: true } });
    setPaths(list.map(mapPath));
  }, []);

  return useMemo(() => ({
    paths,
    auditLog,
    createPath, regeneratePath, editPath, submitPath, requestChanges, approvePath, archivePath, deletePath, addComment, resolveComment, refreshPaths, loaded,
  }), [paths, auditLog, createPath, regeneratePath, editPath, submitPath, requestChanges, approvePath, archivePath, deletePath, addComment, resolveComment, refreshPaths, loaded]);
}

function newComment(actor, text, itemRef) {
  return { id: newId("CMT"), author: actor, at: new Date().toISOString(), text, item_ref: itemRef, reply_to: null, resolved: false, resolved_by: null };
}

export function usePaths() {
  const ctx = useContext(PathsContext);
  if (!ctx) throw new Error("usePaths must be used inside <PathsProvider>");
  return ctx;
}
