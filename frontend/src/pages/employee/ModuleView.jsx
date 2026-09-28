import { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { ArrowLeft, BookOpen, CheckSquare, ClipboardCheck, Check, ExternalLink, Clock3, LockKeyhole, CircleCheck, CircleAlert, ArrowRight, Target } from "../../components/Icons";
import { Card, Badge, Button, ProgressBar, EmptyState, Toast } from "../../components/UI";
import Citation from "../../components/Citation";
import { useLanguage } from "../../contexts/LanguageContext";
import { useEnrollment } from "../../contexts/EnrollmentContext";
import { useDocuments, openStoredFile } from "../../contexts/DocumentsContext";
import { useMyPaths } from "../../hooks/useMyPaths";
import { moduleProgress, nextModule, PASS_RATIO, stageUnlocked } from "../../utils/progress";

/** Study a module: read lessons (with source document references), complete tasks, take quiz */
export default function ModuleView() {
  const { id, moduleId } = useParams();
  const navigate = useNavigate();
  const { t, pick } = useLanguage();
  const { enrollmentFor, markLessonRead, toggleTask, submitQuiz, error } = useEnrollment();
  const { documents, getFile } = useDocuments();
  const [toast, setToast] = useState("");
  const path = useMyPaths().find(p => p.id === id);
  const stageIndex = path ? path.stages.findIndex(s => s.modules.some(m => m.id === moduleId)) : -1;
  const module = stageIndex >= 0 ? path.stages[stageIndex].modules.find(m => m.id === moduleId) : null;

  if (!path || !module) {
    return <EmptyState title={t("err_path_not_found")} action={<Button onClick={() => navigate("/employee/paths")}>{t("back_to_list")}</Button>} />;
  }
  const e = enrollmentFor(path.id);
  const back = () => navigate(`/employee/paths/${path.id}`);

  if (!stageUnlocked(path, stageIndex, e)) {
    return (
      <div>
        <button className="back-btn" onClick={back}><ArrowLeft size={16} /> {t("back_to_path")}</button>
        <Card><EmptyState title={t("stage_locked")} description={t("stage_locked_hint")} action={<Button onClick={back}>{t("back_to_path")}</Button>} /></Card>
      </div>
    );
  }

  const mp = moduleProgress(module, e);
  const lessonsDone = mp.lessonsDone === module.lessons.length;
  const next = mp.complete ? nextModule(path, e) : null;

  const openSource = async (ref) => {
    const doc = documents.find(d => d.id === ref.doc_id) || documents.find(d => d.code === ref.doc && d.status === "active");
    if (!doc) { setToast(t("quote_not_in_repo")); return; }
    try { await openStoredFile(getFile, doc, { page: ref.page }); }
    catch (err) { setToast(t("save_failed", { msg: err.message })); }
  };

  return (
    <div>
      <button className="back-btn" onClick={back}><ArrowLeft size={16} /> {t("back_to_path")}</button>
      {error && <div className="notice notice--danger" role="alert"><CircleAlert size={16} /><span>{t(error)}</span></div>}
      <div className="page-heading">
        <div>
          <span className="eyebrow">{t(`stage_${path.stages[stageIndex].key}`)}{module.doc_code ? ` · ${module.doc_code}` : ""}</span>
          <h1>{pick(module, "title")}</h1>
          <p>{t(module.kind === "assessment" ? "assessment_desc" : "module_desc")}</p>
        </div>
        <div style={{ minWidth: 200 }}><ProgressBar value={mp.percent} showValue /></div>
      </div>

      {mp.complete && (
        <div className="notice notice--success">
          <CircleCheck size={16} />
          <span>{t("module_completed")}</span>
          {next && <Button variant="ghost" onClick={() => navigate(`/employee/paths/${path.id}/modules/${next.module.id}`)}>{t("next_module")}: {pick(next.module, "title")} <ArrowRight size={14} /></Button>}
        </div>
      )}

      {module.learning_objectives?.length > 0 && (
        <section className="learn-section">
          <h2><Target size={18} /> {t("learning_objectives")}</h2>
          <Card><ul className="objective-list">{module.learning_objectives.map((o, i) => <li key={i}>{o}</li>)}</ul></Card>
        </section>
      )}

      {module.lessons.length > 0 && (
        <section className="learn-section">
          <h2><BookOpen size={18} /> {t("lessons")} <span className="cell-sub">{mp.lessonsDone}/{module.lessons.length}</span></h2>
          {module.lessons.map((l, i) => {
            const read = e.lessonsRead.includes(l.id);
            return (
              <Card key={l.id} className={`lesson-card ${read ? "is-read" : ""}`}>
                <div className="card-title-row">
                  <div>
                    <h3>{pick(l, "title") || t("part_n", { n: i + 1 })}</h3>
                    <span className="cell-sub"><Clock3 size={11} /> {t("min_n", { n: l.minutes })}</span>
                  </div>
                  {read ? <Badge tone="green"><Check size={12} /> {t("lesson_read")}</Badge> : null}
                </div>
                <p className="lesson-text">{l.content}</p>
                <Citation reference={l.source_reference} compact verify={false} />
                <div className="review-actions">
                  <Button variant="secondary" onClick={() => openSource(l.source_reference)} icon={<ExternalLink size={14} />}>{t("open_source_doc")}</Button>
                  {!read && <Button onClick={() => markLessonRead(path, l.id)} icon={<Check size={14} />}>{t("mark_read")}</Button>}
                </div>
              </Card>
            );
          })}
        </section>
      )}

      {module.tasks.length > 0 && (
        <section className="learn-section">
          <h2><CheckSquare size={18} /> {t("work_tasks")} <span className="cell-sub">{mp.tasksDone}/{module.tasks.length}</span></h2>
          <Card>
            <p className="cell-sub" style={{ marginTop: 0 }}>{t("tasks_hint")}</p>
            {module.tasks.map(task => {
              const done = e.tasksDone.includes(task.id);
              return (
                <div key={task.id} className="task-row">
                  <label className="checkbox">
                    <input type="checkbox" checked={done} onChange={() => toggleTask(path, task.id)} />
                    <span style={{ textDecoration: done ? "line-through" : "none" }}>{pick(task, "title")}</span>
                  </label>
                  {task.completion_criteria && <p className="task-criteria"><b>{t("completion_criteria")}:</b> {pick(task, "completion_criteria")}</p>}
                  <span className="cell-sub">{task.source_reference.doc} · {task.source_reference.section}</span>
                </div>
              );
            })}
          </Card>
        </section>
      )}

      {module.quiz.length > 0 && (
        <section className="learn-section">
          <h2><ClipboardCheck size={18} /> {t("module_quiz")}</h2>
          {!lessonsDone ? (
            <Card><p className="cell-sub"><LockKeyhole size={13} /> {t("quiz_locked_hint")}</p></Card>
          ) : (
            <QuizBlock path={path} module={module} best={mp.best} onSubmit={answers => submitQuiz(path, module, answers)} />
          )}
        </section>
      )}
      <Toast message={toast} onClose={() => setToast("")} />
    </div>
  );
}

function QuizBlock({ module, best, onSubmit }) {
  const { t, pick } = useLanguage();
  const [answers, setAnswers] = useState({});
  const [result, setResult] = useState(null);
  const [sending, setSending] = useState(false);
  const allAnswered = module.quiz.every(q => answers[q.id] !== undefined);
  // Backend mode grades quiz on server; network errors shown in page alert while keeping quiz state
  const submit = async () => {
    setSending(true);
    try {
      setResult(await onSubmit(answers));
    } catch {
      setResult(null);
    } finally {
      setSending(false);
    }
  };

  if (result) {
    const scorePercent = result.total > 0 ? Math.round((result.score / result.total) * 100) : 0;
    const isWeakArea = !result.passed || scorePercent < 70;

    return (
      <Card className={`quiz-result-card ${result.passed ? "is-pass" : "is-fail"}`}>
        <div className="card-title-row">
          <h3>{t("quiz_score", { c: result.score, n: result.total })} ({scorePercent}%)</h3>
          <Badge tone={result.passed ? "green" : "red"}>{t(result.passed ? "quiz_passed" : "quiz_failed", { n: Math.round(PASS_RATIO * 100) })}</Badge>
        </div>

        {isWeakArea ? (
          <div style={{
            margin: "12px 0 16px",
            padding: "12px 14px",
            background: "rgba(245, 158, 11, 0.08)",
            border: "1px solid rgba(245, 158, 11, 0.3)",
            borderRadius: "var(--radius-md, 8px)"
          }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8, fontWeight: 700, color: "#b45309", marginBottom: 6, fontSize: 13.5 }}>
              <CircleAlert size={16} />
              Weak-Area Detected · {scorePercent}%
            </div>
            <div style={{ fontSize: 13, color: "var(--muted)", lineHeight: 1.5 }}>
              Quiz score is below the mastery threshold (≥ 70%). Follow the recommendations below to reinforce your knowledge:
              <ul style={{ margin: "6px 0 0 18px", padding: 0 }}>
                <li><strong>Review Theory:</strong> Re-read the lessons in this module before re-attempting.</li>
                <li><strong>Verify Standards:</strong> Review the SOP citations and detailed explanations for any incorrect answers below.</li>
                <li><strong>Retake Quiz:</strong> Click <em>"Retake Quiz"</em> below to improve your score and fulfill the module requirements.</li>
              </ul>
            </div>
          </div>
        ) : (
          <div style={{
            margin: "12px 0 16px",
            padding: "10px 14px",
            background: "rgba(16, 185, 129, 0.08)",
            border: "1px solid rgba(16, 185, 129, 0.3)",
            borderRadius: "var(--radius-md, 8px)",
            display: "flex",
            alignItems: "center",
            gap: 8,
            color: "#065f46",
            fontWeight: 600,
            fontSize: 13
          }}>
            <CircleCheck size={16} style={{ color: "#10b981" }} />
            Achieved mastery score ({scorePercent}%). Eligible for completion credit!
          </div>
        )}

        {module.quiz.map((q, i) => {
          const ok = answers[q.id] === q.answer;
          return (
            <div key={q.id} className={`quiz-review ${ok ? "is-ok" : "is-wrong"}`}>
              <strong>{i + 1}. {pick(q, "question")}</strong>
              <span className="cell-sub">
                {ok ? <CircleCheck size={12} /> : <CircleAlert size={12} />} {t("your_answer")}: {q.options[answers[q.id]]}
                {!ok && <> · {t("correct_answer")}: <b>{q.options[q.answer]}</b></>}
              </span>
              {q.explanation && <span className="cell-sub">{t("quiz_explanation")}: {q.explanation}</span>}
              {/* Citation displayed after submission to avoid revealing answers */}
              <Citation reference={q.source_reference} compact verify={false} />
            </div>
          );
        })}
        <div className="review-actions">
          <Button variant="secondary" onClick={() => { setResult(null); setAnswers({}); }}>{t("retake_quiz")}</Button>
        </div>
      </Card>
    );
  }

  return (
    <Card>
      <p className="cell-sub" style={{ marginTop: 0 }}>
        {t("quiz_intro", { n: module.quiz.length, pass: Math.round(PASS_RATIO * 100) })}
        {best && <> · {t("best_score", { c: best.score, n: best.total })}</>}
      </p>
      {module.quiz.map((q, i) => (
        <div key={q.id} className="question-card">
          <span className="question-number">{t("question_label", { n: String(i + 1).padStart(2, "0") })}</span>
          <h3>{pick(q, "question")}</h3>
          <div className="options">
            {q.options.map((o, j) => (
              <button key={j} className={`option ${answers[q.id] === j ? "selected" : ""}`} onClick={() => setAnswers(a => ({ ...a, [q.id]: j }))}>
                <span>{String.fromCharCode(65 + j)}</span>{o}
              </button>
            ))}
          </div>
          <span className="cell-sub">{t("answer_source")} {q.source_reference.doc} · {q.source_reference.section}{q.source_reference.page != null ? ` · ${t("page_abbr")}${q.source_reference.page}` : ""}</span>
        </div>
      ))}
      <div className="review-actions">
        <Button disabled={!allAnswered || sending} onClick={submit}>{t("finish_quiz")}</Button>
      </div>
    </Card>
  );
}
