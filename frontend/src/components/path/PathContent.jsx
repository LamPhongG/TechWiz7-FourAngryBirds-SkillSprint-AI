import { useState } from "react";
import { BookOpen, CheckSquare, ClipboardCheck, ChevronDown, Pencil, Trash2, MessageSquare, Clock3, CircleAlert } from "../Icons";
import { Badge, Button } from "../UI";
import ValidationTag from "../ValidationTag";
import Citation from "../Citation";
import { useLanguage } from "../../contexts/LanguageContext";
import { usePaths, PathError } from "../../contexts/PathsContext";
import { STAGE_TEMPLATES } from "../../data/company";

// Các phép sửa lộ trình (thuần, trả về bản mới)

function mapModule(path, moduleId, fn) {
  return { ...path, stages: path.stages.map(s => ({ ...s, modules: s.modules.map(m => (m.id === moduleId ? fn(m) : m)) })) };
}

function moveModule(path, moduleId, toKey) {
  const module = path.stages.flatMap(s => s.modules).find(m => m.id === moduleId);
  const template = STAGE_TEMPLATES[path.purpose] || STAGE_TEMPLATES.onboarding;
  let stages = path.stages.map(s => ({ ...s, modules: s.modules.filter(m => m.id !== moduleId) }));
  if (!stages.some(s => s.key === toKey)) {
    stages = [...stages, { key: toKey, modules: [] }].sort((a, b) => template.indexOf(a.key) - template.indexOf(b.key));
  }
  stages = stages.map(s => (s.key === toKey ? { ...s, modules: [...s.modules, module] } : s));
  // Giai đoạn rỗng sau khi chuyển không còn ý nghĩa với nhân viên
  return { ...path, stages: stages.filter(s => s.modules.length) };
}

const KIND_FIELD = { lesson: "lessons", task: "tasks", quiz: "quiz" };

/**
 * Nội dung lộ trình: giai đoạn → học phần → bài học / nhiệm vụ / câu hỏi.
 * editable = true thì cho sửa, xoá, chuyển học phần sang giai đoạn khác (mọi thay đổi ghi audit).
 */
export default function PathContent({ path, editable = false, statusByItem = {}, commentCounts = {}, onComment }) {
  const { t, pick } = useLanguage();
  const { editPath } = usePaths();
  const [open, setOpen] = useState(() => new Set([path.stages[0]?.modules[0]?.id]));
  const [editing, setEditing] = useState(null);
  const [error, setError] = useState("");
  const template = STAGE_TEMPLATES[path.purpose] || STAGE_TEMPLATES.onboarding;

  const apply = (mutate, details) => {
    setError("");
    try {
      editPath(path.id, mutate, details);
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

  const save = (module, kind, item, patch) => {
    if (apply(p => mapModule(p, module.id, m => ({ ...m, [KIND_FIELD[kind]]: m[KIND_FIELD[kind]].map(x => (x.id === item.id ? { ...x, ...patch } : x)) })), { op: "update", kind, item: item.id })) {
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
                    {module.doc_code && <Badge tone="default">{module.doc_code}</Badge>}
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
                    {module.lessons.length > 0 && <h4><BookOpen size={14} /> {t("lessons")} ({module.lessons.length})</h4>}
                    {module.lessons.map((l, i) => {
                      const label = `${mTitle} › ${l.title || t("part_n", { n: i + 1 })}`;
                      return (
                        <div key={l.id} className="content-item">
                          <div className="content-item__row">
                            <div>
                              <strong>{l.title || t("part_n", { n: i + 1 })}</strong>
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
                          <strong className="task-text">{task.title}</strong>
                          {itemActions(module, "task", task, `${mTitle} › ${task.title.slice(0, 60)}`)}
                        </div>
                        {editing === task.id
                          ? <TaskForm task={task} onCancel={() => setEditing(null)} onSave={patch => save(module, "task", task, patch)} />
                          : <Citation reference={task.source_reference} compact verify={false} />}
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
  const [title, setTitle] = useState(task.title);
  return (
    <div className="inline-form">
      <textarea rows={3} value={title} onChange={e => setTitle(e.target.value)} />
      <FormButtons onCancel={onCancel} onSave={() => onSave({ title: title.trim() })} disabled={!title.trim()} />
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
      {/* Câu hỏi đã sửa tay dùng chung một nội dung cho cả hai ngôn ngữ */}
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
