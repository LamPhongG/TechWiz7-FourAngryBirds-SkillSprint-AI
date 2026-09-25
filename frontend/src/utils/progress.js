// Tiến độ học của nhân viên trên một lộ trình đã phát hành.
// Học phần hoàn thành = đọc hết bài học + làm hết nhiệm vụ + đạt bài kiểm tra.
// Giai đoạn sau chỉ mở khi mọi học phần của các giai đoạn trước đã hoàn thành (học đúng luồng).

export const PASS_RATIO = 0.7;

export const emptyEnrollment = () => ({ lessonsRead: [], tasksDone: [], quiz: {}, startedAt: null, completedAt: null });

export function bestAttempt(enrollment, moduleId) {
  const attempts = enrollment?.quiz?.[moduleId] || [];
  return attempts.reduce((best, a) => (!best || a.score / a.total > best.score / best.total ? a : best), null);
}

export function scoreQuiz(questions, answers) {
  const correct = questions.filter(q => answers[q.id] === q.answer).length;
  return { score: correct, total: questions.length, passed: questions.length > 0 && correct / questions.length >= PASS_RATIO };
}

export function moduleProgress(module, enrollment) {
  const e = enrollment || emptyEnrollment();
  const lessonsDone = module.lessons.filter(l => e.lessonsRead.includes(l.id)).length;
  const tasksDone = module.tasks.filter(t => e.tasksDone.includes(t.id)).length;
  const best = bestAttempt(e, module.id);
  const quizPassed = module.quiz.length === 0 || (!!best && best.score / best.total >= PASS_RATIO);
  const steps = module.lessons.length + module.tasks.length + (module.quiz.length ? 1 : 0);
  const done = lessonsDone + tasksDone + (module.quiz.length && quizPassed ? 1 : 0);
  return {
    lessonsDone, tasksDone, best, quizPassed,
    percent: steps ? Math.round((done / steps) * 100) : 100,
    complete: lessonsDone === module.lessons.length && tasksDone === module.tasks.length && quizPassed,
  };
}

export function stageUnlocked(path, stageIndex, enrollment) {
  return path.stages.slice(0, stageIndex).every(s => s.modules.every(m => moduleProgress(m, enrollment).complete));
}

export function pathProgress(path, enrollment) {
  const modules = path.stages.flatMap(s => s.modules);
  const done = modules.filter(m => moduleProgress(m, enrollment).complete).length;
  return { done, total: modules.length, percent: modules.length ? Math.round((done / modules.length) * 100) : 0, complete: modules.length > 0 && done === modules.length };
}

/** Học phần tiếp theo cần học: học phần chưa xong đầu tiên trong giai đoạn đang mở */
export function nextModule(path, enrollment) {
  for (let i = 0; i < path.stages.length; i++) {
    if (!stageUnlocked(path, i, enrollment)) return null;
    const m = path.stages[i].modules.find(x => !moduleProgress(x, enrollment).complete);
    if (m) return { module: m, stage: path.stages[i] };
  }
  return null;
}
