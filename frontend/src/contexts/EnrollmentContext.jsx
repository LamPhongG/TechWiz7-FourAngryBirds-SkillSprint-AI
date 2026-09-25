import { createContext, useCallback, useContext, useMemo, useState } from "react";
import { useAuth } from "../hooks/useAuth";
import { readJson, STORAGE_KEYS, writeJson } from "../services/localStore";
import { sanitizeEnrollments } from "../services/sanitize";
import { emptyEnrollment, pathProgress, scoreQuiz } from "../utils/progress";

// Tiến độ học theo từng nhân viên và từng lộ trình: bài đã đọc, nhiệm vụ đã làm, các lần làm bài kiểm tra
const EnrollmentContext = createContext(null);

export function EnrollmentProvider({ children }) {
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

  /** Chấm bài và lưu lần làm; trả về kết quả để trang hiển thị */
  const submitQuiz = useCallback((path, module, answers) => {
    const result = scoreQuiz(module.quiz, answers);
    update(path, e => ({
      ...e,
      quiz: { ...e.quiz, [module.id]: [...(e.quiz[module.id] || []), { at: new Date().toISOString(), answers, score: result.score, total: result.total }] },
    }));
    return result;
  }, [update]);

  const value = useMemo(() => ({
    enrollmentFor: pathId => mine[pathId] || emptyEnrollment(),
    markLessonRead, toggleTask, submitQuiz,
  }), [mine, markLessonRead, toggleTask, submitQuiz]);

  return <EnrollmentContext.Provider value={value}>{children}</EnrollmentContext.Provider>;
}

export function useEnrollment() {
  const ctx = useContext(EnrollmentContext);
  if (!ctx) throw new Error("useEnrollment must be used inside <EnrollmentProvider>");
  return ctx;
}
