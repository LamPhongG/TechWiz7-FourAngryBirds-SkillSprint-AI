import { useEffect, useState } from "react";
import { BrainCircuit, Check, CircleAlert, Loader2, Sparkles, X } from "../Icons";
import { EngineBadge } from "./Badges";
import { useLanguage } from "../../contexts/LanguageContext";

// Generation progress for AI path drafting, powered by backend background job (GET /paths/jobs/{id}).
// All figures reflect actual pipeline runs — no simulated timer progress bars.

export const STEPS = ["sources", "analysis", "plan", "modules", "coverage", "saving"];
// Drafting individual modules is the most time-consuming step (each module makes 2 AI calls)
const WEIGHT = { sources: 5, analysis: 5, plan: 5, modules: 75, coverage: 5, saving: 5 };
const MODULE_PHASE_SHARE = { waiting: 0, lessons: 0.25, quiz: 0.6, done: 1, fallback: 1 };

export function jobPercent(job) {
  if (!job) return 0;
  if (job.status === "done") return 100;
  const { steps, modules = [] } = job.state;
  let total = 0;
  for (const step of STEPS) {
    const status = steps[step];
    if (status === "done" || status === "skipped") total += WEIGHT[step];
    else if (step === "modules" && modules.length) {
      total += WEIGHT.modules * modules.reduce((sum, m) => sum + (MODULE_PHASE_SHARE[m.phase] ?? 0), 0) / modules.length;
    } else if (status === "active") total += WEIGHT[step] / 2;
  }
  return Math.min(99, Math.round(total));
}

/** AI error code (QUOTA_EXCEEDED, UPSTREAM_UNAVAILABLE...) -> readable message; preserves unknown codes */
export function llmErrorLabel(t, code) {
  if (!code) return "";
  const key = `llm_error_${code.startsWith("BLOCKED_") ? "BLOCKED" : code}`;
  const text = t(key);
  return text === key ? code : text;
}

function clock(ms) {
  const s = Math.floor(ms / 1000);
  return `${String(Math.floor(s / 60)).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`;
}

function StepIcon({ status }) {
  if (status === "done") return <span className="gp-dot gp-dot--done"><Check size={13} /></span>;
  if (status === "active") return <span className="gp-dot gp-dot--active"><Loader2 size={13} className="spin" /></span>;
  if (status === "failed") return <span className="gp-dot gp-dot--failed"><X size={13} /></span>;
  return <span className={`gp-dot gp-dot--${status}`} />;
}

function stepDetail(step, job, t) {
  const s = job?.state || {};
  const modules = s.modules || [];
  switch (step) {
    case "sources":
      return s.sources ? t("gp_sources_done", { n: s.sources.count }) : t("gp_sources_desc");
    case "analysis":
      if (!s.analysis) return t("gp_analysis_desc");
      return t("gp_analysis_done", { chunks: s.analysis.chunks, docs: s.analysis.used_documents, excluded: s.analysis.excluded_chunks })
        + (s.analysis.off_role_sections ? ` · ${t("gp_analysis_off_role", { n: s.analysis.off_role_sections })}` : "");
    case "plan":
      return modules.length ? t("gp_plan_done", { modules: modules.length, stages: new Set(modules.map(m => m.stage)).size }) : t("gp_plan_desc");
    case "modules": {
      const finished = modules.filter(m => m.phase === "done" || m.phase === "fallback").length;
      return modules.length ? t("gp_modules_progress", { done: finished, total: modules.length }) : t("gp_modules_desc");
    }
    case "coverage":
      if (s.coverage) return t("gp_coverage_done", { taught: s.coverage.taught.length, total: s.coverage.total, missing: s.coverage.mandatory_not_taught.length });
      return s.steps?.coverage === "skipped" ? t("gp_coverage_skipped") : t("gp_coverage_desc");
    default:
      return t("gp_saving_desc");
  }
}

function ModuleRow({ module, t, pick }) {
  const { phase } = module;
  const busy = phase === "lessons" || phase === "quiz";
  return (
    <li className={`gp-module gp-module--${phase}`}>
      <span className="gp-module__icon">
        {busy ? <Loader2 size={14} className="spin" /> : phase === "done" ? <Check size={14} /> : phase === "fallback" ? <CircleAlert size={14} /> : null}
      </span>
      <div className="gp-module__body">
        <strong>{module.doc} · {pick({ title: module.title, titleEn: module.title_en }, "title")}</strong>
        <span className="cell-sub">
          {t(`stage_${module.stage}`)} · {t(`gp_phase_${phase}`)}
          {(phase === "done" || phase === "fallback") && ` · ${t("gp_module_counts", { l: module.lessons ?? 0, t: module.tasks ?? 0, q: module.questions ?? 0 })}`}
          {phase === "fallback" && module.error && ` · ${llmErrorLabel(t, module.error)}`}
          {module.dropped > 0 && ` · ${t("gp_module_dropped", { n: module.dropped })}`}
        </span>
      </div>
    </li>
  );
}

/**
 * @param {object}   props.job       job from backend (null upon click before response)
 * @param {string}   props.subtitle  current configuration: role · purpose · duration · document count
 * @param {string}   [props.error]   translated error message when job fails
 * @param {Function} [props.onBack]  return to configuration screen after error
 * @param {boolean}  [props.compact] in "Regenerate" dialog: hides module progress table
 */
export default function GenerationProgress({ job, subtitle, error, onBack, compact = false }) {
  const { t, pick } = useLanguage();
  const [now, setNow] = useState(() => Date.now());
  const [startedAt] = useState(() => Date.now());
  const running = !error && job?.status !== "done";
  useEffect(() => {
    if (!running) return undefined;
    const timer = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(timer);
  }, [running]);

  const percent = jobPercent(job);
  const steps = job?.state.steps || Object.fromEntries(STEPS.map((s, i) => [s, i === 0 ? "active" : "pending"]));
  const modules = job?.state.modules || [];
  const fallbacks = modules.filter(m => m.phase === "fallback");
  const elapsed = job && !running ? job.elapsed_ms : now - startedAt;
  const state = error ? "failed" : job?.status === "done" ? "done" : "running";

  return (
    <section className={`gen-progress gen-progress--${state} ${compact ? "gen-progress--compact" : ""}`} aria-live="polite">
      <header className="gen-progress__head">
        <div className="gen-progress__icon">{state === "done" ? <Check size={22} /> : state === "failed" ? <CircleAlert size={22} /> : <Sparkles size={22} />}</div>
        <div className="gen-progress__title">
          <h2>{t(`gp_title_${state}`)}</h2>
          {subtitle && <p>{subtitle}</p>}
        </div>
        <div className="gen-progress__meta">
          {job?.state.engine && <EngineBadge engine={job.state.engine} />}
          <span className="gen-progress__clock">{clock(elapsed)}</span>
          <strong className="gen-progress__percent">{percent}%</strong>
        </div>
      </header>

      <div className="gen-progress__bar" role="progressbar" aria-valuemin={0} aria-valuemax={100} aria-valuenow={percent}>
        <div style={{ width: `${percent}%` }} />
      </div>

      {fallbacks.length > 0 && !error && (
        <div className="notice notice--warning">
          <CircleAlert size={16} />
          <span>{t("gp_fallback_notice", { n: fallbacks.length, total: modules.length, reason: llmErrorLabel(t, fallbacks[0].error) })}</span>
        </div>
      )}
      {error && (
        <div className="notice notice--danger">
          <CircleAlert size={16} /><span>{error}</span>
          {onBack && <button type="button" className="link-btn" onClick={onBack}>{t("gp_back_to_config")}</button>}
        </div>
      )}

      <div className="gen-progress__grid">
        <ol className="gp-steps">
          {STEPS.map(step => (
            <li key={step} className={`gp-step gp-step--${steps[step]}`}>
              <StepIcon status={steps[step]} />
              <div>
                <strong>{t(`gp_step_${step}`)}</strong>
                <span className="cell-sub">{stepDetail(step, job, t)}</span>
              </div>
            </li>
          ))}
        </ol>

        {!compact && (
          <div className="gp-board">
            <div className="gp-board__head">
              <BrainCircuit size={16} />
              <strong>{t("gp_board_title")}</strong>
              {modules.length > 0 && <span className="cell-sub">{t("gp_board_hint")}</span>}
            </div>
            {modules.length === 0
              ? <p className="cell-sub gp-board__empty">{t("gp_board_waiting")}</p>
              : <ul className="gp-modules">{modules.map(m => <ModuleRow key={m.id} module={m} t={t} pick={pick} />)}</ul>}
          </div>
        )}
      </div>
    </section>
  );
}
