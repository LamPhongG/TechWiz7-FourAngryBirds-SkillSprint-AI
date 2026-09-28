import { useMemo, useState } from "react";
import { Check, X, CircleAlert, ShieldAlert } from "../Icons";
import { Badge, Button, Card, StatCard } from "../UI";
import { useLanguage } from "../../contexts/LanguageContext";

/**
 * GenAI / Python comparison per requirement, from GET /paths/{id}/comparison.
 * A field with `match: null` has no independent data on one side and is shown as such, never as a match.
 */
const RESULT_KEY = {
  "Match": "match", "Mismatch": "mismatch", "Missing Requirement": "missing", "Unsupported Requirement": "unsupported",
  "Contradiction Detected": "contradiction", "Source Support Missing": "source_missing", "Outdated Source": "outdated",
  "Not Covered (Optional)": "optional",
};
const RESULT_TONE = { match: "green", optional: "default", mismatch: "orange", outdated: "orange" };
export const STATUS_KEY = {
  "Verified": "verified", "Verified with Warning": "verified_warning", "Incomplete": "incomplete", "Unsupported": "unsupported",
  "Contradictory": "contradictory", "Manual Review Required": "manual_review",
};
const STATUS_TONE = { verified: "green", verified_warning: "orange" };
const pct = value => (value == null ? "—" : `${value}%`);

export default function DualComparisonTable({ report }) {
  const { t } = useLanguage();
  const [filter, setFilter] = useState("all");
  const rows = report?.rows || [];
  const counts = useMemo(() => rows.reduce((acc, r) => {
    const key = RESULT_KEY[r.result];
    acc[key] = (acc[key] || 0) + 1;
    return acc;
  }, {}), [rows]);
  const visible = useMemo(() => (filter === "all" ? rows : rows.filter(r => RESULT_KEY[r.result] === filter)), [rows, filter]);

  if (!report) {
    return <Card><p className="cell-sub" style={{ textAlign: "center", padding: 24 }}>{t("cmp_loading")}</p></Card>;
  }

  const show = value => {
    if (value == null || (Array.isArray(value) && value.length === 0)) return "—";
    if (typeof value === "boolean") return t(value ? "cmp_yes" : "cmp_no");
    if (Array.isArray(value)) return value.map(v => (typeof v === "string" && t(`stage_${v}`) !== `stage_${v}` ? t(`stage_${v}`) : v)).join(", ");
    if (typeof value === "string" && t(`stage_${value}`) !== `stage_${value}`) return t(`stage_${value}`);
    return String(value);
  };
  const { summary } = report;

  return (
    <div className="dual-comparison-view">
      <div className="card" style={{ display: "flex", justifyContent: "space-between", flexWrap: "wrap", gap: 16, padding: "16px 20px", marginBottom: 20 }}>
        <div>
          <div className="eyebrow">{t("cmp_decision_title")}</div>
          <div style={{ display: "flex", alignItems: "center", gap: 12, marginTop: 4 }}>
            <h2 style={{ margin: 0, fontSize: 20 }}>{report.path_title}</h2>
            <Badge tone={STATUS_TONE[STATUS_KEY[report.final_verification_status]] || "red"}>{t(`cmp_status_${STATUS_KEY[report.final_verification_status]}`)}</Badge>
          </div>
          <p className="cell-sub" style={{ margin: "4px 0 0" }}>
            {t("cmp_role_line", { role: report.role_name, total: report.total_requirements, mandatory: report.mandatory_requirements })}
          </p>
          {!report.genai_claims_available && <p className="cell-sub" style={{ margin: "6px 0 0" }}>{t("cmp_no_claims")}</p>}
        </div>
        <div style={{ display: "flex", gap: 20 }}>
          {[["cmp_coverage", report.coverage_score], ["cmp_traceability", report.source_traceability_score],
            ["cmp_consistency", report.requirement_consistency_score]].map(([key, value]) => (
            <div key={key} style={{ textAlign: "right" }}>
              <div className="cell-sub">{t(key)}</div>
              <div style={{ fontSize: 20, fontWeight: 800 }}>{pct(value)}</div>
            </div>
          ))}
        </div>
      </div>

      <div className="stat-grid" style={{ marginBottom: 20 }}>
        <StatCard label={t("cmp_result_match")} value={summary.matches} icon={Check} tone="green" />
        <StatCard label={t("cmp_result_mismatch")} value={summary.mismatches + summary.outdated} icon={CircleAlert} tone="orange" />
        <StatCard label={t("cmp_result_missing")} value={summary.missing} icon={X} tone={summary.missing ? "red" : "default"} />
        <StatCard label={t("cmp_problems")} value={summary.unsupported + summary.source_missing + summary.contradictions}
          icon={ShieldAlert} tone={summary.unsupported + summary.source_missing + summary.contradictions ? "red" : "default"} />
      </div>

      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 16, alignItems: "center" }}>
        <span className="cell-sub">{t("cmp_filter")}</span>
        <Button variant={filter === "all" ? "primary" : "ghost"} size="sm" onClick={() => setFilter("all")}>
          {t("cmp_all")} ({rows.length})
        </Button>
        {Object.entries(counts).map(([key, n]) => (
          <Button key={key} variant={filter === key ? "primary" : "ghost"} size="sm" onClick={() => setFilter(key)}>
            {t(`cmp_result_${key}`)} ({n})
          </Button>
        ))}
      </div>

      <Card>
        <div style={{ overflowX: "auto" }}>
          <table className="data-table" style={{ width: "100%", fontSize: 13 }}>
            <thead>
              <tr>
                <th>{t("cmp_col_requirement")}</th>
                <th>{t("cmp_col_field")}</th>
                <th>{t("cmp_col_genai")}</th>
                <th>{t("cmp_col_python")}</th>
                <th>{t("cmp_col_result")}</th>
              </tr>
            </thead>
            <tbody>
              {visible.map(row => {
                const key = RESULT_KEY[row.result];
                return (
                  <tr key={row.requirement_id} style={{ verticalAlign: "top" }}>
                    <td style={{ minWidth: 220 }}>
                      <code>{row.requirement_id}</code>{" "}
                      <Badge tone={row.mandatory ? "red" : "default"}>{t(row.mandatory ? "cmp_mandatory" : "cmp_optional")}</Badge>
                      <div style={{ marginTop: 4 }}>{row.python_ground_truth?.text || "—"}</div>
                      <div className="cell-sub">
                        {row.source_document ? `${row.source_document}${row.source_section ? ` §${row.source_section}` : ""}` : t("cmp_not_in_matrix")}
                        {row.priority && ` · ${row.priority}`}
                      </div>
                    </td>
                    <td>{row.field_comparisons.map(f => <div key={f.field}>{t(`cmp_field_${f.field}`)}</div>)}</td>
                    <td>{row.field_comparisons.map(f => <div key={f.field}>{show(f.genai)}</div>)}</td>
                    <td>
                      {row.field_comparisons.map(f => (
                        <div key={f.field} style={{ display: "flex", gap: 6, alignItems: "center" }}>
                          {f.match === true && <Check size={13} style={{ color: "var(--success, #10b981)" }} aria-label={t("cmp_yes")} />}
                          {f.match === false && <X size={13} style={{ color: "var(--danger, #ef4444)" }} aria-label={t("cmp_no")} />}
                          {f.match == null && <span className="cell-sub" title={t("cmp_no_data")}>—</span>}
                          <span>{show(f.gt)}</span>
                        </div>
                      ))}
                    </td>
                    <td style={{ minWidth: 150 }}>
                      <Badge tone={RESULT_TONE[key] || "red"}>{t(`cmp_result_${key}`)}</Badge>
                      <div style={{ marginTop: 6 }}>
                        <Badge tone={STATUS_TONE[STATUS_KEY[row.validation_status]] || "red"}>{t(`cmp_status_${STATUS_KEY[row.validation_status]}`)}</Badge>
                      </div>
                      {row.failed_fields.length > 0 && (
                        <div className="cell-sub" style={{ marginTop: 6 }}>
                          {t("cmp_differs_on", { fields: row.failed_fields.map(f => t(`cmp_field_${f}`)).join(", ") })}
                        </div>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}
