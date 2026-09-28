import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { useAuth } from "../hooks/useAuth";
import { usePaths } from "./PathsContext";
import { apiRequest, backendEnabled } from "../services/apiClient";
import { mapEnrollment } from "../services/apiMappers";
import { readJson, STORAGE_KEYS, writeJson } from "../services/localStore";
import { sanitizeEnrollments } from "../services/sanitize";
import { emptyEnrollment, pathProgress, scoreQuiz } from "../utils/progress";

// Learning progress by employee and path: read lessons, completed tasks, quiz attempts.
// Backend mode: enrollment records reside on server (GET /me/enrollments); server grades quizzes and computes completion.
const EnrollmentContext = createContext(null);

const base = pathId => `/me/enrollments/${encodeURIComponent(pathId)}`;

// Mode is fixed at build time, so provider always calls the same hook
const useEnrollmentSource = backendEnabled() ? useBackendEnrollments : useBrowserEnrollments;

export function EnrollmentProvider({ children }) {
  const value = useEnrollmentSource();
  return <EnrollmentContext.Provider value={value}>{children}</EnrollmentContext.Provider>;
}

function useBrowserEnrollments() {
  const { user } = useAuth();
  const [all, setAll] = useState(() => sanitizeEnrollments(readJson(STORAGE_KEYS.enrollments, {})));
  const userKey = user ? String(user.id) : null;
  const mine = useMemo(() => (userKey ? all[userKey] || {} : {}), [all, userKey]);

  const update = useCallback((path, mutate) => {
    if (!userKey) return false;
    const current = all[userKey]?.[path.id] || emptyEnrollment();
    let next = mutate({ ...current, startedAt: current.startedAt || new Date().toISOString() });
    if (!next.completedAt && pathProgress(path, next).complete) next = { ...next, completedAt: new Date().toISOString() };
    const nextAll = { ...all, [userKey]: { ...(all[userKey] || {}), [path.id]: next } };
    setAll(nextAll);
    return writeJson(STORAGE_KEYS.enrollments, nextAll);
  }, [all, userKey]);

  const markLessonRead = useCallback((path, lessonId) => update(path, e => (
    e.lessonsRead.includes(lessonId) ? e : { ...e, lessonsRead: [...e.lessonsRead, lessonId] }
  )), [update]);

  const toggleTask = useCallback((path, taskId) => update(path, e => ({
    ...e,
    tasksDone: e.tasksDone.includes(taskId) ? e.tasksDone.filter(x => x !== taskId) : [...e.tasksDone, taskId],
  })), [update]);

  /** Grade quiz and save attempt; returns result for page display */
  const submitQuiz = useCallback((path, module, answers) => {
    const result = scoreQuiz(module.quiz, answers);
    update(path, e => ({
      ...e,
      quiz: { ...e.quiz, [module.id]: [...(e.quiz[module.id] || []), { at: new Date().toISOString(), answers, score: result.score, total: result.total }] },
    }));
    return result;
  }, [update]);

  return useMemo(() => ({
    enrollmentFor: pathId => mine[pathId] || emptyEnrollment(),
    markLessonRead, toggleTask, submitQuiz, error: "",
    // Explore and self-enroll in paths is only available when backend is active
    enroll: () => Promise.reject(new Error("backend_only")),
  }), [mine, markLessonRead, toggleTask, submitQuiz]);
}

function useBackendEnrollments() {
  const { user } = useAuth();
  const { refreshPaths } = usePaths();
  const [byPath, setByPath] = useState({});
  const [error, setError] = useState("");
  const isEmployee = user?.userRole === "employee";

  useEffect(() => {
    if (!isEmployee) { setByPath({}); return undefined; }
    let active = true;
    apiRequest("/me/enrollments")
      .then(rows => { if (active) setByPath(Object.fromEntries(rows.map(r => [r.path_id, mapEnrollment(r)]))); })
      .catch(e => { if (active) setError(e.code || "err_network"); });
    return () => { active = false; };
  }, [isEmployee, user?.id]);

  // Each action returns the latest record from server (status, completion % calculated by server)
  const save = useCallback(async request => {
    setError("");
    try {
      const row = await request();
      const enrollment = row.enrollment || row;
      setByPath(current => ({ ...current, [enrollment.path_id]: mapEnrollment(enrollment) }));
      return row;
    } catch (e) {
      setError(e.code || "err_network");
      throw e;
    }
  }, []);

  const markLessonRead = useCallback((path, lessonId) => save(() => apiRequest(
    `${base(path.id)}/lessons/${encodeURIComponent(lessonId)}`, { method: "POST" })), [save]);

  const toggleTask = useCallback((path, taskId) => {
    const done = !(byPath[path.id]?.tasksDone || []).includes(taskId);
    return save(() => apiRequest(`${base(path.id)}/tasks/${encodeURIComponent(taskId)}`, { method: "PUT", body: { done } }));
  }, [byPath, save]);

  const submitQuiz = useCallback(async (path, module, answers) => {
    const res = await save(() => apiRequest(`${base(path.id)}/quizzes/${encodeURIComponent(module.id)}`,
      { method: "POST", body: { answers } }));
    return { score: res.score, total: res.total, passed: res.passed };
  }, [save]);

  /** Self-enroll in department path (Explore paths); path immediately appears in My Paths */
  const enroll = useCallback(async pathId => {
    const row = await save(() => apiRequest(`/explore/paths/${encodeURIComponent(pathId)}/enroll`, { method: "POST" }));
    await refreshPaths();
    return row;
  }, [save, refreshPaths]);

  return useMemo(() => ({
    enrollmentFor: pathId => byPath[pathId] || emptyEnrollment(),
    markLessonRead, toggleTask, submitQuiz, enroll, error,
  }), [byPath, markLessonRead, toggleTask, submitQuiz, enroll, error]);
}

export function useEnrollment() {
  const ctx = useContext(EnrollmentContext);
  if (!ctx) throw new Error("useEnrollment must be used inside <EnrollmentProvider>");
  return ctx;
}
