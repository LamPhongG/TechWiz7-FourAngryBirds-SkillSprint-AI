import { useState } from "react";
import { BookOpen, CheckSquare, ClipboardCheck, ChevronDown, Pencil, Trash2, MessageSquare, Clock3, CircleAlert, Target } from "../Icons";
import { Badge, Button } from "../UI";
import ValidationTag from "../ValidationTag";
import Citation from "../Citation";
import { useLanguage } from "../../contexts/LanguageContext";
import { usePaths, PathError } from "../../contexts/PathsContext";
import { stageTemplate } from "../../data/company";

// Path mutation helpers (pure functions, returning new instance)

function mapModule(path, moduleId, fn) {
  return { ...path, stages: path.stages.map(s => ({ ...s, modules: s.modules.map(m => (m.id === moduleId ? fn(m) : m)) })) };
}

function moveModule(path, moduleId, toKey) {
  const module = path.stages.flatMap(s => s.modules).find(m => m.id === moduleId);
  const template = stageTemplate(path.purpose, path.duration_days);
  let stages = path.stages.map(s => ({ ...s, modules: s.modules.filter(m => m.id !== moduleId) }));
  if (!stages.some(s => s.key === toKey)) {
    stages = [...stages, { key: toKey, modules: [] }].sort((a, b) => template.indexOf(a.key) - template.indexOf(b.key));
  }
  stages = stages.map(s => (s.key === toKey ? { ...s, modules: [...s.modules, module] } : s));
  // Empty stage after moving has no meaning for learners
  return { ...path, stages: stages.filter(s => s.modules.length) };
}

const KIND_FIELD = { lesson: "lessons", task: "tasks", quiz: "quiz" };

/**
 * Path content: stage -> module -> lesson / task / quiz.
 * When editable = true, allows editing, deleting, moving modules to other stages (all audited).
 */
export default function PathContent({ path, editable = false, statusByItem = {}, commentCounts = {}, onComment }) {
  const { t, pick } = useLanguage();
  const { editPath } = usePaths();
  const [open, setOpen] = useState(() => new Set([path.stages[0]?.modules[0]?.id]));
  const [editing, setEditing] = useState(null);
  const [error, setError] = useState("");
  // Only allow moving modules between stages within the HR-selected duration template
  const template = stageTemplate(path.purpose, path.duration_days);

  // Awaits both synchronous operations (browser mode) and API calls (backend mode)
  const apply = async (mutate, details) => {
    setError("");
    try {
      await editPath(path.id, mutate, details);
      return true;
    } catch (e) {
      setError(e instanceof PathError ? t(e.key, e.vars) : e.message);
      return false;
    }
  };

  const toggle = id => setOpen(prev => {
    const next = new Set(prev);
    if (next.has(id)) next.delete(id); else next.add(id);
    return next;
  });

  const remove = (module, kind, item) => {
    if (!window.confirm(t("confirm_delete_item"))) return;
    apply(p => mapModule(p, module.id, m => ({ ...m, [KIND_FIELD[kind]]: m[KIND_FIELD[kind]].filter(x => x.id !== item.id) })), { op: "delete", kind, item: item.id });
  };

  const save = async (module, kind, item, patch) => {
    // When updating title / criteria, clear legacy fields to maintain consistency
    let change = kind !== "quiz" && "title" in patch ? { ...patch, titleEn: undefined } : patch;
    if ("completion_criteria" in patch) change = { ...change, completion_criteriaEn: undefined };
    if (await apply(p => mapModule(p, module.id, m => ({ ...m, [KIND_FIELD[kind]]: m[KIND_FIELD[kind]].map(x => (x.id === item.id ? { ...x, ...change } : x)) })), { op: "update", kind, item: item.id })) {
      setEditing(null);
    }
  };

  const itemActions = (module, kind, item, label) => (
    <div className="item-actions">
      <ValidationTag status={statusByItem[item.id] || "pending"} showLabel={false} />
      {onComment && (
        <button className="icon-btn" title={t("action_comment")} aria-label={t("action_comment")} onClick={() => onComment({ id: item.id, label })}>
          <MessageSquare size={15} />{commentCounts[item.id] > 0 && <i className="icon-count">{commentCounts[item.id]}</i>}
        </button>
      )}
      {editable && <button className="icon-btn" title={t("action_edit")} aria-label={t("action_edit")} onClick={() => setEditing(item.id)}><Pencil size={15} /></button>}
      {editable && <button className="icon-btn" title={t("action_delete")} aria-label={t("action_delete")} onClick={() => remove(module, kind, item)}><Trash2 size={15} /></button>}
    </div>
  );

  return (
    <div className="path-content">
      {error && <div className="notice notice--danger"><CircleAlert size={16} /><span>{error}</span></div>}
      {path.stages.map((stage, si) => (
        <section key={stage.key} className="stage-block">
          <header className="stage-block__head">
            <span className="stage-index">{si + 1}</span>
            <div>
              <strong>{t(`stage_${stage.key}`)}</strong>
              <span className="cell-sub">{t("modules_count", { n: stage.modules.length })}</span>
            </div>
          </header>

          {stage.modules.map(module => {
            const isOpen = open.has(module.id);
            const mTitle = pick(module, "title");
            return (
              <article key={module.id} className={`module-card ${module.kind === "assessment" ? "module-card--assessment" : ""}`}>
                <div className="module-card__head">
                  <button className="module-card__toggle" onClick={() => toggle(module.id)}>
                    <ChevronDown size={16} className={isOpen ? "rotated" : ""} />
                    <strong>{mTitle}</strong>
                  </button>
                  <div className="module-card__meta">
                    {module.doc_code && <Badge tone="default">{module.doc_code}{module.source_sections?.length > 0 && ` · §${module.source_sections.join(", §")}`}</Badge>}
                    {module.mandatory && <Badge tone="red">{t("module_mandatory")}</Badge>}
                    <span className="cell-sub">{t("module_summary", { l: module.lessons.length, t: module.tasks.length, q: module.quiz.length })}</span>
                    {onComment && (
                      <button className="icon-btn" title={t("action_comment")} aria-label={t("action_comment")} onClick={() => onComment({ id: module.id, label: mTitle })}>
                        <MessageSquare size={15} />{commentCounts[module.id] > 0 && <i className="icon-count">{commentCounts[module.id]}</i>}
                      </button>
                    )}
                    {editable && (
                      <select className="filter-select" value={stage.key} title={t("move_to_stage")} aria-label={t("move_to_stage")}
                        onChange={e => apply(p => moveModule(p, module.id, e.target.value), { op: "move", module: module.id, from: stage.key, to: e.target.value })}>
                        {template.map(k => <option key={k} value={k}>{t(`stage_${k}`)}</option>)}
                      </select>
                    )}
                  </div>
                </div>

                {isOpen && (
                  <div className="module-card__body">
                    <ModuleBrief module={module} />
                    {module.lessons.length > 0 && <h4><BookOpen size={14} /> {t("lessons")} ({module.lessons.length})</h4>}
                    {module.lessons.map((l, i) => {
                      const lTitle = pick(l, "title") || t("part_n", { n: i + 1 });
                      const label = `${mTitle} › ${lTitle}`;
                      return (
                        <div key={l.id} className="content-item">
                          <div className="content-item__row">
                            <div>
                              <strong>{lTitle}</strong>
                              <span className="cell-sub"><Clock3 size={11} /> {t("min_n", { n: l.minutes })}</span>
                            </div>
                            {itemActions(module, "lesson", l, label)}
                          </div>
                          {editing === l.id ? (
                            <LessonForm lesson={l} onCancel={() => setEditing(null)} onSave={patch => save(module, "lesson", l, patch)} />
                          ) : (
                            <details>
                              <summary>{t("show_content")}</summary>
                              <p className="lesson-text">{l.content}</p>
                              <Citation reference={l.source_reference} compact />
                            </details>
                          )}
                        </div>
                      );
                    })}

                    {module.tasks.length > 0 && <h4><CheckSquare size={14} /> {t("work_tasks")} ({module.tasks.length})</h4>}
                    {module.tasks.map(task => (
                      <div key={task.id} className="content-item">
                        <div className="content-item__row">
                          <strong className="task-text">{pick(task, "title")}</strong>
                          {itemActions(module, "task", task, `${mTitle} › ${pick(task, "title").slice(0, 60)}`)}
                        </div>
                        {editing === task.id ? (
                          <TaskForm task={task} onCancel={() => setEditing(null)} onSave={patch => save(module, "task", task, patch)} />
                        ) : (
                          <>
                            {task.completion_criteria
                              ? <p className="task-criteria"><b>{t("completion_criteria")}:</b> {pick(task, "completion_criteria")}</p>
                              : <p className="task-criteria text-danger"><CircleAlert size={12} /> {t("completion_criteria_missing")}</p>}
                            <Citation reference={task.source_reference} compact verify={false} />
                          </>
                        )}
                      </div>
                    ))}

                    {module.quiz.length > 0 && <h4><ClipboardCheck size={14} /> {t("quiz_questions")} ({module.quiz.length})</h4>}
                    {module.quiz.map((q, i) => (
                      <div key={q.id} className="content-item">
                        <div className="content-item__row">
                          <strong>{i + 1}. {pick(q, "question")}</strong>
                          {itemActions(module, "quiz", q, `${mTitle} › ${t("question_label", { n: i + 1 })}`)}
                        </div>
                        {editing === q.id ? (
                          <QuizForm question={q} onCancel={() => setEditing(null)} onSave={patch => save(module, "quiz", q, patch)} />
                        ) : (
                          <>
                            <ol className="option-list" type="A">
                              {q.options.map((o, j) => <li key={j} className={j === q.answer ? "is-correct" : ""}>{o}</li>)}
                            </ol>
                            {q.explanation && <p className="cell-sub">{t("quiz_explanation")}: {q.explanation}</p>}
                            <Citation reference={q.source_reference} compact verify={false} />
                          </>
                        )}
                      </div>
                    ))}
                    {module.kind !== "assessment" && module.lessons.length === 0 && <p className="cell-sub">{t("module_no_lessons")}</p>}
                  </div>
                )}
              </article>
            );
          })}
        </section>
      ))}
    </div>
  );
}

/** Learning objectives and matrix requirements covered by module (attached per document section) */
function ModuleBrief({ module }) {
  const { t } = useLanguage();
  const objectives = module.learning_objectives || [];
  const reqs = module.requirement_ids || [];
  if (!objectives.length && !reqs.length) return null;
  return (
    <div className="module-brief">
      {objectives.length > 0 && (
        <>
          <h4><Target size={14} /> {t("learning_objectives")}</h4>
          <ul>{objectives.map((o, i) => <li key={i}>{o}</li>)}</ul>
        </>
      )}
      {reqs.length > 0 && (
        <p className="cell-sub">{t("covers_requirements")}: {reqs.map(r => <span key={r} className="item-chip">{r}</span>)}</p>
      )}
    </div>
  );
}

function LessonForm({ lesson, onSave, onCancel }) {
  const { t } = useLanguage();
  const [title, setTitle] = useState(lesson.title);
  const [content, setContent] = useState(lesson.content);
  return (
    <div className="inline-form">
      <label>{t("col_title")}<input value={title} onChange={e => setTitle(e.target.value)} /></label>
      <label>{t("lesson_content")}<textarea rows={8} value={content} onChange={e => setContent(e.target.value)} /></label>
      <FormButtons onCancel={onCancel} onSave={() => onSave({ title: title.trim(), content: content.trim() })} disabled={!content.trim()} />
    </div>
  );
}

function TaskForm({ task, onSave, onCancel }) {
  const { t, pick } = useLanguage();
  const [title, setTitle] = useState(task.title);
  const [criteria, setCriteria] = useState(pick(task, "completion_criteria") || "");
  return (
    <div className="inline-form">
      <label>{t("task_action")}<textarea rows={3} value={title} onChange={e => setTitle(e.target.value)} /></label>
      <label>{t("completion_criteria")}<textarea rows={2} value={criteria} onChange={e => setCriteria(e.target.value)} placeholder={t("completion_criteria_hint")} /></label>
      {/* Missing criteria blocks publication in Python verification; do not allow empty criteria */}
      <FormButtons onCancel={onCancel} onSave={() => onSave({ title: title.trim(), completion_criteria: criteria.trim() })}
        disabled={!title.trim() || !criteria.trim()} />
    </div>
  );
}

function QuizForm({ question, onSave, onCancel }) {
  const { t, pick } = useLanguage();
  const [text, setText] = useState(pick(question, "question"));
  const [options, setOptions] = useState(question.options);
  const [answer, setAnswer] = useState(question.answer);
  const valid = text.trim() && options.every(o => o.trim()) && new Set(options.map(o => o.trim())).size === options.length;
  return (
    <div className="inline-form">
      <label>{t("question_text")}<textarea rows={3} value={text} onChange={e => setText(e.target.value)} /></label>
      {options.map((o, i) => (
        <label key={i} className="option-edit">
          <input type="radio" name={`ans-${question.id}`} checked={answer === i} onChange={() => setAnswer(i)} aria-label={t("correct_answer")} />
          <input value={o} onChange={e => setOptions(list => list.map((x, j) => (j === i ? e.target.value : x)))} />
        </label>
      ))}
      <span className="cell-sub">{t("quiz_edit_hint")}</span>
      {/* Manually edited questions use the edited content for both language fields */}
      <FormButtons onCancel={onCancel} disabled={!valid}
        onSave={() => onSave({ question: text.trim(), questionEn: text.trim(), options: options.map(o => o.trim()), answer })} />
    </div>
  );
}

function FormButtons({ onSave, onCancel, disabled }) {
  const { t } = useLanguage();
  return (
    <div className="modal-actions">
      <Button variant="secondary" onClick={onCancel}>{t("cancel")}</Button>
      <Button onClick={onSave} disabled={disabled}>{t("save_changes")}</Button>
    </div>
  );
}
