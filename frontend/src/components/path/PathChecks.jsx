import { useState } from "react";
import { BrainCircuit, Database, CircleAlert, CircleCheck, ShieldAlert } from "../Icons";
import { Badge, Card, SectionHeader } from "../UI";
import ValidationTag from "../ValidationTag";
import InjectionFlagList from "../InjectionFlagList";
import { FinalStatusBadge, CoverageScore } from "./Badges";
import { useLanguage } from "../../contexts/LanguageContext";
import { normalizeForMatch } from "../../utils/chunker";
import { allModules } from "../../utils/pathGenerator";

const SEVERITY = {
  verified: "ok", outdated_source: "warning", pending: "warning",
  hallucination: "critical", contradiction: "critical", source_missing: "critical",
};

function ReasonList({ reasons }) {
  const { t } = useLanguage();
  return <ul className="reason-list">{reasons.map((r, i) => <li key={i}>{t(r.key, r.vars)}</li>)}</ul>;
}

/** Tóm tắt kết quả kiểm định: trạng thái cuối, lý do, và có được phát hành không */
export function ChecksSummary({ checks }) {
  const { t } = useLanguage();
  return (
    <div className="checks-summary">
      <FinalStatusBadge status={checks.final_status} large />
      <ReasonList reasons={checks.reasons} />
      {checks.blocking && (
        <div className="notice notice--danger"><ShieldAlert size={16} /><span>{t("blocking_notice")}</span></div>
      )}
    </div>
  );
}

// Cắt đoạn chunk quanh câu trích và tô sáng câu trích
function SourceExcerpt({ chunk, quote }) {
  const text = chunk.content;
  const idx = normalizeForMatch(text).indexOf(normalizeForMatch(quote));
  if (idx < 0) return <p className="source-excerpt">{text.slice(0, 400)}{text.length > 400 ? "…" : ""}</p>;
  // Vị trí sau chuẩn hoá chỉ xấp xỉ vị trí gốc; đủ để lấy ngữ cảnh xung quanh
  const start = Math.max(0, idx - 150);
  const before = text.slice(start, idx);
  const match = text.slice(idx, idx + quote.length);
  const after = text.slice(idx + quote.length, idx + quote.length + 150);
  return <p className="source-excerpt">{start > 0 && "…"}{before}<mark>{match}</mark>{after}{idx + quote.length + 150 < text.length && "…"}</p>;
}

function aiText(entry, t, pick) {
  if (entry.kind === "lesson") return `${entry.item.title ? `${entry.item.title}: ` : ""}${entry.item.content.slice(0, 260)}${entry.item.content.length > 260 ? "…" : ""}`;
  if (entry.kind === "task") return entry.item.title;
  return `${pick(entry.item, "question")} → ${t("correct_answer")}: ${entry.item.options?.[entry.item.answer] ?? "—"}`;
}

/**
 * Bốn nhóm kiểm tra cho Reviewer: kiến thức (so sánh nội dung AI với tài liệu gốc), luồng, chức năng, an toàn.
 */
export default function PathChecks({ path, checks }) {
  const { t, pick } = useLanguage();
  const [tab, setTab] = useState("knowledge");
  const [onlyIssues, setOnlyIssues] = useState(true);
  const modules = Object.fromEntries(allModules(path).map(m => [m.id, m]));

  const issues = checks.knowledge.filter(k => k.status !== "verified");
  const rows = onlyIssues ? issues : checks.knowledge;
  const flowErrors = checks.flow.filter(f => f.severity === "error");
  const cov = checks.coverage;
  const TABS = [
    ["knowledge", t("check_knowledge"), issues.length],
    ["flow", t("check_flow"), checks.flow.length],
    ["function", t("check_function"), cov ? cov.requiredDocs.filter(d => !d.covered).length + cov.topics.filter(x => !x.covered).length : 0],
    ["safety", t("check_safety"), checks.injection.length + (path.excluded_chunks?.length || 0)],
  ];

  return (
    <div className="path-checks">
      <div className="filter-tabs check-tabs">
        {TABS.map(([key, label, n]) => (
          <button key={key} className={tab === key ? "active" : ""} onClick={() => setTab(key)}>
            {label} {n > 0 && <em className="tab-count">{n}</em>}
          </button>
        ))}
      </div>

      {tab === "knowledge" && (
        <Card>
          <SectionHeader title={t("check_knowledge_title")} subtitle={t("check_knowledge_desc")} />
          <div className="dual-compare__toolbar">
            <div className="filter-tabs">
              <button className={onlyIssues ? "active" : ""} onClick={() => setOnlyIssues(true)}>{t("cmp_only_issues")} ({issues.length})</button>
              <button className={!onlyIssues ? "active" : ""} onClick={() => setOnlyIssues(false)}>{t("filter_all")} ({checks.knowledge.length})</button>
            </div>
            <div className="dual-compare__legend">
              <span><i className="legend-dot legend-dot--critical" />{t("cmp_legend_critical")}</span>
              <span><i className="legend-dot legend-dot--warning" />{t("cmp_legend_warning")}</span>
              <span><i className="legend-dot legend-dot--ok" />{t("cmp_legend_ok")}</span>
            </div>
          </div>
          <div className="dual-compare__head">
            <span><BrainCircuit size={15} /> {t("col_genai")}</span>
            <span><Database size={15} /> {t("col_ground_truth")}</span>
          </div>
          {rows.length === 0 && <p className="quote-check quote-check--ok"><CircleCheck size={13} /> {t("knowledge_all_ok")}</p>}
          <div className="dual-compare">
            {rows.map(entry => {
              const ref = entry.source_reference || {};
              return (
                <div key={entry.id} className={`cmp-row cmp-row--${SEVERITY[entry.status]}`}>
                  <div className="cmp-row__title">
                    <div>
                      <span className="cell-sub">{t(`kind_${entry.kind}`)} · {pick(modules[entry.module_id], "title")}</span>
                    </div>
                    <ValidationTag status={entry.status} />
                  </div>
                  <div className="cmp-row__cols">
                    <div className="cmp-cell">
                      <span className="cmp-cell__label"><BrainCircuit size={12} /> {t("col_genai")}</span>
                      <p className="cmp-value">{aiText(entry, t, pick)}</p>
                      {ref.exact_quote && <blockquote className="citation__quote">{ref.exact_quote}</blockquote>}
                      <span className="cell-sub">{ref.doc} {ref.section ? `· ${ref.section}` : ""} {ref.page != null ? `· ${t("page_abbr")}${ref.page}` : ""}</span>
                    </div>
                    <div className="cmp-cell">
                      <span className="cmp-cell__label"><Database size={12} /> {t("col_ground_truth")}</span>
                      {entry.chunk ? (
                        <>
                          <span className="cell-sub">{entry.chunk.chunk_id}{entry.chunk.page != null ? ` · ${t("page_abbr")}${entry.chunk.page}` : ""}{entry.chunk.heading ? ` · ${entry.chunk.heading}` : ""}</span>
                          <SourceExcerpt chunk={entry.chunk} quote={ref.exact_quote} />
                        </>
                      ) : (
                        <p className="quote-check quote-check--error"><CircleAlert size={12} /> {t(`knowledge_msg_${entry.status}`)}</p>
                      )}
                      {entry.status === "contradiction" && <p className="quote-check quote-check--error"><CircleAlert size={12} /> {t("knowledge_msg_contradiction")}</p>}
                      {entry.status === "outdated_source" && <p className="quote-check quote-check--warning"><CircleAlert size={12} /> {t("knowledge_msg_outdated_source")}</p>}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </Card>
      )}

      {tab === "flow" && (
        <Card>
          <SectionHeader title={t("check_flow_title")} subtitle={t("check_flow_desc")} />
          <ol className="flow-overview">
            {path.stages.map(s => (
              <li key={s.key}>
                <strong>{t(`stage_${s.key}`)}</strong>
                <span className="cell-sub">{s.modules.map(m => pick(m, "title")).join(" → ")}</span>
              </li>
            ))}
          </ol>
          {checks.flow.length === 0 ? (
            <p className="quote-check quote-check--ok"><CircleCheck size={13} /> {t("flow_all_ok")}</p>
          ) : (
            <ul className="issue-list">
              {checks.flow.map((f, i) => (
                <li key={i} className={`issue issue--${f.severity === "error" ? "error" : "warning"}`}>
                  <CircleAlert size={13} /> {t(f.key, { ...f.vars, stage: f.vars?.stage ? t(`stage_${f.vars.stage}`) : undefined })}
                </li>
              ))}
            </ul>
          )}
          {flowErrors.length > 0 && <p className="cell-sub">{t("flow_errors_block")}</p>}
        </Card>
      )}

      {tab === "function" && (
        <Card>
          <SectionHeader title={t("check_function_title")} subtitle={t("check_function_desc")} action={cov && <CoverageScore score={cov.score} />} />
          {!cov ? <div className="notice notice--warning"><CircleAlert size={16} /><span>{t("coverage_pending_backend")}</span></div> : (
            <>
              <div className="field-label">{t("coverage_required_docs", { n: cov.requiredDocs.filter(d => d.covered).length, total: cov.requiredDocs.length })}</div>
              <div className="chip-row">
                {cov.requiredDocs.map(d => (
                  <span key={d.code} className={`doc-chip ${d.covered ? "doc-chip--ok" : "doc-chip--missing"}`}>
                    {d.covered ? <CircleCheck size={12} /> : <CircleAlert size={12} />}{d.code}
                  </span>
                ))}
              </div>
              <div className="field-label" style={{ marginTop: 12 }}>{t("coverage_topics", { n: cov.topics.filter(x => x.covered).length, total: cov.topics.length })}</div>
              <ul className="topic-list">
                {cov.topics.map(topic => (
                  <li key={topic.id} className={topic.covered ? "is-covered" : ""}>
                    {topic.covered ? <CircleCheck size={13} /> : <CircleAlert size={13} />}
                    <strong>{pick(topic, "label")}</strong>
                    {topic.covered && <span className="cell-sub">“{topic.matchedKeyword}”</span>}
                  </li>
                ))}
              </ul>
            </>
          )}
        </Card>
      )}

      {tab === "safety" && (
        <Card>
          <SectionHeader title={t("check_safety_title")} subtitle={t("check_safety_desc")} />
          <div className="field-label">{t("injection_in_content")}</div>
          <InjectionFlagList flags={checks.injection} />
          <div className="field-label" style={{ marginTop: 14 }}>{t("excluded_chunks_title", { n: path.excluded_chunks?.length || 0 })}</div>
          {path.excluded_chunks?.length ? (
            <div className="flag-list">
              {path.excluded_chunks.map(c => (
                <div key={c.chunk_id} className="flag-item">
                  <div><Badge tone="orange">{c.doc}</Badge><span className="cell-sub">{c.chunk_id} · {c.rule_ids.map(r => t(`inj_rule_${r}`)).join(", ")}</span></div>
                </div>
              ))}
            </div>
          ) : <p className="cell-sub">{t("excluded_chunks_none")}</p>}
        </Card>
      )}
    </div>
  );
}
