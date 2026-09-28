import { CircleAlert } from "../Icons";
import { Badge } from "../UI";
import { EngineBadge } from "./Badges";
import { llmErrorLabel } from "./GenerationProgress";
import { useLanguage } from "../../contexts/LanguageContext";

/**
 * Pipeline 1 report returned by backend (path.generation): model, tokens, duration, and whether each module
 * was authored by Gemini or used local draft, and how many items were pruned due to unverifiable citations.
 * Helps Reviewers identify which sections require closer scrutiny.
 */
export default function GenerationReport({ generation }) {
  const { t } = useLanguage();
  if (!generation) return <p className="cell-sub" style={{ padding: 16, textAlign: "center" }}>{t("gen_none")}</p>;

  const modules = generation.modules || [];
  const fallbacks = modules.filter(m => m.engine !== "gemini");
  const dropped = modules.reduce((n, m) => n + Object.values(m.dropped || {}).reduce((a, b) => a + b, 0), 0);
  const repaired = modules.reduce((n, m) => n + (m.repaired_quotes || 0), 0);
  const coverage = generation.requirements;
  const offRole = generation.off_role_sections || [];

  return (
    <div>
      {generation.engine === "gemini" && fallbacks.length > 0 && (
        <div className="notice notice--warning"><CircleAlert size={16} /><span>{t("gen_fallback_notice", { n: fallbacks.length })}</span></div>
      )}
      <dl className="meta-list">
        <dt>{t("gen_engine")}</dt>
        <dd><EngineBadge engine={generation.engine} /> {generation.model && <span className="cell-sub">{generation.model}</span>}</dd>
        <dt>{t("prompt_version")}</dt><dd>{generation.prompt_version}</dd>
        <dt>{t("gen_language")}</dt><dd>English</dd>
        <dt>{t("gen_duration")}</dt><dd>{(generation.duration_ms / 1000).toFixed(1)} s</dd>
        {generation.engine === "gemini" && <><dt>{t("gen_tokens")}</dt><dd>{t("gen_tokens_value", { input: generation.tokens?.input ?? 0, output: generation.tokens?.output ?? 0 })}</dd></>}
        {generation.engine === "gemini" && <><dt>{t("gen_grounding")}</dt><dd>{t("gen_grounding_value", { dropped, repaired })}</dd></>}
        {coverage && <><dt>{t("gen_requirements")}</dt><dd>{t("gen_requirements_value", { taught: coverage.taught.length, assessed: coverage.assessed.length, total: coverage.total, mandatory: coverage.mandatory })}</dd></>}
      </dl>
      {/* Python independently maps section ↔ matrix according to document section, ignoring self-reported model claims */}
      {generation.mandatory_omitted?.length > 0 && (
        <div className="notice notice--warning"><CircleAlert size={16} /><span>{t("gen_mandatory_omitted", { list: generation.mandatory_omitted.join(", ") })}</span></div>
      )}
      {coverage?.mandatory_not_taught.length > 0 && (
        <div className="notice notice--warning"><CircleAlert size={16} /><span>{t("gen_requirements_not_taught", { list: coverage.mandatory_not_taught.join(", ") })}</span></div>
      )}
      {coverage?.mandatory_not_assessed.length > 0 && (
        <div className="notice notice--info"><CircleAlert size={16} /><span>{t("gen_requirements_not_assessed", { list: coverage.mandatory_not_assessed.join(", ") })}</span></div>
      )}
      {offRole.length > 0 && (
        // Sections for other roles are not sent to AI: Reviewer can clearly see what was dropped and why
        <details className="gen-offrole">
          <summary>{t("gen_off_role_title", { n: offRole.length })}</summary>
          <ul>{offRole.map(s => <li key={`${s.doc}-${s.section}`}><b>{s.doc} §{s.section}</b> {s.heading} <span className="cell-sub">· {t("gen_off_role_chunks", { n: s.chunks })}</span></li>)}</ul>
        </details>
      )}

      <div className="table-wrap" style={{ marginTop: 12 }}>
        <table className="audit-table">
          <thead>
            <tr>
              <th>{t("gen_col_module")}</th>
              <th>{t("gen_col_engine")}</th>
              <th>{t("gen_col_items")}</th>
              <th>{t("gen_col_dropped")}</th>
            </tr>
          </thead>
          <tbody>
            {modules.map(m => (
              <tr key={m.module_id}>
                <td><strong>{m.doc}</strong><span className="cell-sub">{m.module_id}</span></td>
                <td>
                  <EngineBadge engine={m.engine} fallback={Boolean(m.error)} />
                  {m.quiz_engine && m.quiz_engine !== m.engine && <span className="cell-sub">{t("gen_quiz_fallback")}</span>}
                  {m.error && <span className="cell-sub text-danger">{t("gen_error", { code: llmErrorLabel(t, m.error) })}</span>}
                </td>
                <td>{m.lessons != null ? t("gen_items_value", { l: m.lessons, t: m.tasks, q: m.questions }) : "—"}</td>
                <td>
                  {Object.entries(m.dropped || {}).map(([reason, n]) => <Badge key={reason} tone="orange">{t(`gen_drop_${reason}`)} × {n}</Badge>)}
                  {m.repaired_quotes > 0 && <Badge tone="default">{t("gen_repaired", { n: m.repaired_quotes })}</Badge>}
                  {m.model_flagged?.length > 0 && <Badge tone="red">{t("gen_model_flagged", { list: m.model_flagged.join(", ") })}</Badge>}
                  {!m.repaired_quotes && !Object.keys(m.dropped || {}).length && "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
