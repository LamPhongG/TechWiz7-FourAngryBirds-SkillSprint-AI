import { useEffect, useMemo, useState } from "react";
import {
  BarChart3, Printer, Users, BookOpen, ShieldAlert, Award, Check, X, CircleAlert, Search, Layers3,
  FileSpreadsheet, RouteIcon, FileText, Target, ShieldCheck,
} from "../../components/Icons";
import { Card, StatCard, Button, Badge, ProgressBar, EmptyState } from "../../components/UI";
import { FinalStatusBadge } from "../../components/path/Badges";
import { STATUS_KEY } from "../../components/path/DualComparisonTable";
import { useLanguage } from "../../contexts/LanguageContext";
import { useAuth } from "../../hooks/useAuth";
import { apiBlob, apiRequest, backendEnabled } from "../../services/apiClient";
import { DEPARTMENTS } from "../../data/company";
import { exportToCsv, printReportToPdf } from "../../utils/exportHelpers";
import { formatLocalDate } from "../../utils/helpers";

// Every figure comes from the backend reports (SRS Step 51-53, 62). A missing value is a dash, never 0% or an
// invented number (SRS 1.8 #12).
const pct = value => (value == null ? "—" : `${value}%`);
const mean = values => {
  const known = values.filter(v => v != null);
  return known.length ? Math.round(known.reduce((a, b) => a + b, 0) / known.length) : null;
};
const ENDPOINTS = {
  learners: "/learners", coverage: "/reports/role-coverage", quizzes: "/reports/quiz-analytics",
  knowledge: "/reports/documents", alerts: "/reports/alerts", comparison: "/reports/comparison",
};
const EMPTY = Object.fromEntries(Object.keys(ENDPOINTS).map(k => [k, []]));
const LIFECYCLE_TONE = { active: "green", upcoming: "blue" };
const QUIZ_TONE = { ok: "green", weak: "orange", no_attempts: "default" };
const rowKey = (r, i) => r.enrollment_id || r.role_id || (r.module_id && `${r.path_id}-${r.module_id}`) || r.id || r.path_id || i;

export default function HrReports() {
  const { t, tv, pick, locale } = useLanguage();
  const { user } = useAuth();
  const [tab, setTab] = useState("learners");
  const [data, setData] = useState(EMPTY);
  const [loading, setLoading] = useState(backendEnabled());
  const [failed, setFailed] = useState(false);
  const [search, setSearch] = useState("");
  const [dept, setDept] = useState("all");

  useEffect(() => {
    if (!backendEnabled()) return undefined;
    let mounted = true;
    Promise.all(Object.entries(ENDPOINTS).map(([key, url]) => apiRequest(url).then(rows => [key, rows || []])))
      .then(entries => { if (mounted) setData(Object.fromEntries(entries)); })
      .catch(() => { if (mounted) setFailed(true); })
      .finally(() => { if (mounted) setLoading(false); });
    return () => { mounted = false; };
  }, []);

  const tabs = useMemo(() => {
    const date = value => (value ? formatLocalDate(value, locale) : "—");
    const decision = value => t(`cmp_status_${STATUS_KEY[value]}`);
    const citedItems = data.knowledge.reduce((acc, x) => acc + x.cited_items, 0);
    // Weighted by cited items, so a document cited once does not weigh as much as one cited a hundred times.
    const citationAccuracy = citedItems
      ? Math.round(data.knowledge.reduce((acc, x) => acc + (x.citation_accuracy ?? 0) * x.cited_items, 0) / citedItems)
      : null;
    return {
      learners: {
        title: "rep_title_learners", subtitle: "rep_sub_learners", file: "report_learners", dept: r => r.department_code,
        kpis: [
          { label: "rep_kpi_learners", value: rows => rows.length, icon: Users, tone: "purple" },
          { label: "rep_kpi_completed", value: rows => rows.filter(r => r.status === "completed").length, icon: Award, tone: "green" },
          { label: "rep_kpi_in_progress", value: rows => rows.filter(r => r.status === "in_progress").length, icon: RouteIcon, tone: "blue" },
          { label: "rep_kpi_certificates", value: rows => rows.filter(r => r.certificate).length, icon: ShieldCheck, tone: "orange" },
        ],
        columns: [
          { label: "rep_col_employee", text: r => `${r.name} (${r.email})`, cell: r => <><strong>{r.name}</strong><div className="cell-sub">{r.email}</div></> },
          { label: "rep_col_department", text: r => tv(r.department_code), cell: r => <>{tv(r.department_code)}<div className="cell-sub">{r.job_title}</div></> },
          { label: "rep_col_path", text: r => r.path_title },
          { label: "rep_col_progress", text: r => pct(r.percent),
            cell: r => <div style={{ display: "flex", alignItems: "center", gap: 8 }}><ProgressBar value={r.percent} max={100} /><span>{r.percent}%</span></div> },
          { label: "rep_col_quiz", text: r => pct(r.best_quiz_percent) },
          { label: "rep_col_certificate", text: r => t(r.certificate ? "rep_cert_issued" : "rep_cert_not_yet"),
            cell: r => (r.certificate ? <Badge tone="green">{t("rep_cert_issued")}</Badge> : <span className="cell-sub">{t("rep_cert_not_yet")}</span>) },
          { label: "rep_col_status", text: r => t(`rep_enrollment_${r.status}`),
            cell: r => <Badge tone={r.status === "completed" ? "green" : "blue"}>{t(`rep_enrollment_${r.status}`)}</Badge> },
          { label: "rep_col_completed_at", text: r => date(r.completed_at) },
        ],
      },
      coverage: {
        title: "rep_title_coverage", subtitle: "rep_sub_coverage", file: "report_role_coverage", dept: r => r.department,
        kpis: [
          { label: "rep_kpi_roles", value: rows => rows.length, icon: Target, tone: "purple" },
          { label: "rep_kpi_full_coverage", value: rows => rows.filter(r => r.coverage_score === 100).length, icon: Check, tone: "green" },
          { label: "rep_kpi_avg_coverage", value: rows => pct(mean(rows.map(r => r.coverage_score))), icon: Layers3, tone: "blue" },
          { label: "rep_kpi_roles_without_path", value: rows => rows.filter(r => r.path_id == null).length, icon: CircleAlert, tone: "orange" },
        ],
        columns: [
          { label: "rep_col_role_code", text: r => r.role_id, cell: r => <code>{r.role_id}</code> },
          { label: "rep_col_role", text: r => pick(r, "role_name") },
          { label: "rep_col_department", text: r => tv(r.department) },
          { label: "rep_col_path", text: r => (r.path_id ? pick(r, "path_title") : t("rep_no_published_path")),
            cell: r => (r.path_id ? pick(r, "path_title") : <span className="cell-sub">{t("rep_no_published_path")}</span>) },
          { label: "rep_col_covered", text: r => (r.path_id ? `${r.covered_requirements}/${r.mandatory_requirements}` : "—") },
          { label: "rep_col_coverage", text: r => pct(r.coverage_score) },
          { label: "rep_col_traceability", text: r => pct(r.traceability_score) },
          { label: "rep_col_verification", text: r => r.final_status || "—",
            cell: r => (r.final_status ? <FinalStatusBadge status={r.final_status} /> : "—") },
        ],
      },
      quizzes: {
        title: "rep_title_quizzes", subtitle: "rep_sub_quizzes", file: "report_quizzes",
        kpis: [
          { label: "rep_kpi_quiz_modules", value: rows => rows.length, icon: BookOpen, tone: "purple" },
          { label: "rep_kpi_avg_pass_rate", value: rows => pct(mean(rows.map(r => r.pass_rate))), icon: Award, tone: "green" },
          { label: "rep_kpi_attempts", value: rows => rows.reduce((acc, r) => acc + r.attempts, 0), icon: Check, tone: "blue" },
          { label: "rep_kpi_weak_modules", value: rows => rows.filter(r => r.status === "weak").length, icon: CircleAlert, tone: "orange" },
        ],
        columns: [
          { label: "rep_col_path", text: r => pick(r, "path_title") },
          { label: "rep_col_module", text: r => `${t(`stage_${r.stage_key}`)} · ${pick(r, "module_title")}`,
            cell: r => <><strong>{pick(r, "module_title")}</strong><div className="cell-sub">{t(`stage_${r.stage_key}`)}</div></> },
          { label: "rep_col_questions", text: r => r.quiz_count },
          { label: "rep_col_attempts", text: r => r.attempts },
          { label: "rep_col_pass_rate", text: r => pct(r.pass_rate) },
          { label: "rep_col_avg_score", text: r => pct(r.avg_score) },
          { label: "rep_col_assessment", text: r => t(`rep_quiz_${r.status}`),
            cell: r => <Badge tone={QUIZ_TONE[r.status]}>{t(`rep_quiz_${r.status}`)}</Badge> },
        ],
      },
      knowledge: {
        title: "rep_title_knowledge", subtitle: "rep_sub_knowledge", file: "report_documents",
        kpis: [
          { label: "rep_kpi_documents", value: rows => rows.length, icon: FileText, tone: "purple" },
          { label: "rep_kpi_chunks", value: rows => rows.reduce((acc, r) => acc + r.chunks_count, 0), icon: Layers3, tone: "blue" },
          { label: "rep_kpi_citation_accuracy", value: () => pct(citationAccuracy), icon: Check, tone: "green" },
          { label: "rep_kpi_uncited", value: rows => rows.filter(r => r.cited_items === 0).length, icon: ShieldCheck, tone: "orange" },
        ],
        columns: [
          { label: "rep_col_doc_code", text: r => r.code, cell: r => <code>{r.code}</code> },
          { label: "rep_col_doc_title", text: r => pick(r, "title") },
          { label: "rep_col_category", text: r => r.category, cell: r => <Badge tone="purple">{r.category}</Badge> },
          { label: "rep_col_version", text: r => `v${r.version}` },
          { label: "rep_col_chunks", text: r => r.chunks_count },
          { label: "rep_col_paths_citing", text: r => r.referenced_in_paths },
          { label: "rep_col_citation_accuracy", text: r => pct(r.citation_accuracy),
            cell: r => <><strong>{pct(r.citation_accuracy)}</strong>{r.cited_items > 0 && <div className="cell-sub">{t("rep_items", { n: r.cited_items })}</div>}</> },
          { label: "rep_col_lifecycle", text: r => t(`rep_lifecycle_${r.lifecycle}`),
            cell: r => <Badge tone={LIFECYCLE_TONE[r.lifecycle] || "orange"}>{t(`rep_lifecycle_${r.lifecycle}`)}</Badge> },
        ],
      },
      alerts: {
        title: "rep_title_alerts", subtitle: "rep_sub_alerts", file: "report_alerts",
        kpis: [
          { label: "rep_kpi_alerts", value: rows => rows.length, icon: ShieldAlert, tone: "purple" },
          { label: "rep_kpi_injections", value: rows => rows.filter(r => r.type === "prompt_injection").length, icon: ShieldCheck, tone: "red" },
          { label: "rep_kpi_open", value: rows => rows.filter(r => r.status === "open").length, icon: CircleAlert, tone: "orange" },
          { label: "rep_kpi_excluded", value: rows => rows.filter(r => r.type === "excluded_chunks").length, icon: Check, tone: "green" },
        ],
        columns: [
          { label: "rep_col_alert_id", text: r => r.id, cell: r => <code>{r.id}</code> },
          { label: "rep_col_date", text: r => date(r.date) },
          { label: "rep_col_alert_type", text: r => t(`rep_alert_${r.type}`), cell: r => <strong>{t(`rep_alert_${r.type}`)}</strong> },
          { label: "rep_col_severity", text: r => t(`rep_severity_${r.severity}`),
            cell: r => <Badge tone={r.severity === "high" ? "red" : r.severity === "medium" ? "orange" : "blue"}>{t(`rep_severity_${r.severity}`)}</Badge> },
          { label: "rep_col_source", text: r => r.source },
          { label: "rep_col_details", text: r => (r.type === "prompt_injection" ? r.details : t("rep_items", { n: r.details })) },
          { label: "rep_col_status", text: r => t(`rep_alert_status_${r.status}`),
            cell: r => <Badge tone={r.status === "open" ? "red" : "green"}>{t(`rep_alert_status_${r.status}`)}</Badge> },
        ],
      },
      comparison: {
        title: "rep_title_comparison", subtitle: "rep_sub_comparison", file: "report_comparison_summary", dept: r => r.department,
        kpis: [
          { label: "rep_kpi_compared_paths", value: rows => rows.length, icon: Layers3, tone: "purple" },
          { label: "rep_kpi_verified", value: rows => rows.filter(r => r.decision === "Verified").length, icon: Check, tone: "green" },
          { label: "rep_kpi_warning", value: rows => rows.filter(r => r.decision === "Verified with Warning").length, icon: CircleAlert, tone: "orange" },
          { label: "rep_kpi_not_verified", value: rows => rows.filter(r => !["Verified", "Verified with Warning"].includes(r.decision)).length, icon: X, tone: "red" },
        ],
        columns: [
          { label: "rep_col_path_id", text: r => r.path_id, cell: r => <code>{r.path_id}</code> },
          { label: "rep_col_path", text: r => pick(r, "path_title"),
            cell: r => <>{pick(r, "path_title")}{!r.genai_claims_available && <div className="cell-sub">{t("rep_no_genai_claims")}</div>}</> },
          { label: "rep_col_role", text: r => `${r.role} · ${tv(r.department)}`, cell: r => <>{r.role}<div className="cell-sub">{tv(r.department)}</div></> },
          { label: "cmp_result_match", text: r => r.matches },
          { label: "cmp_result_mismatch", text: r => r.mismatches },
          { label: "cmp_result_missing", text: r => r.missing },
          { label: "cmp_problems", text: r => r.unsupported },
          { label: "rep_col_coverage", text: r => pct(r.coverage_score) },
          { label: "rep_col_decision", text: r => decision(r.decision),
            cell: r => <Badge tone={r.decision === "Verified" ? "green" : r.decision === "Verified with Warning" ? "orange" : "red"}>{decision(r.decision)}</Badge> },
        ],
      },
    };
  }, [data, t, tv, pick, locale]);

  const current = tabs[tab];
  const rows = useMemo(() => {
    const q = search.trim().toLowerCase();
    return data[tab].filter(r => (dept === "all" || !current.dept || current.dept(r) === dept)
      && (!q || current.columns.some(c => String(c.text(r) ?? "").toLowerCase().includes(q))));
  }, [data, tab, current, search, dept]);

  const exportCsv = () => exportToCsv(current.file, current.columns.map(c => t(c.label)), rows.map(r => current.columns.map(c => c.text(r))));
  const exportPdf = () => printReportToPdf({
    title: t(current.title), subtitle: t(current.subtitle),
    kpis: current.kpis.map(k => ({ label: t(k.label), value: k.value(rows) })),
    headers: current.columns.map(c => t(c.label)), rows: rows.map(r => current.columns.map(c => c.text(r))),
    metadata: { [t("rep_exported_by")]: user?.name || "" },
  });
  const exportRequirementCsv = async () => {
    const url = URL.createObjectURL(await apiBlob("/reports/comparison.csv"));
    const a = Object.assign(document.createElement("a"), { href: url, download: "genai_python_comparison.csv" });
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="reports-page">
      <div className="page-heading" style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: 16 }}>
        <div>
          <span className="eyebrow">{t(`role_${user?.userRole || "hr"}`)} · {t("nav_workspace")}</span>
          <h1 style={{ display: "flex", alignItems: "center", gap: 10 }}><BarChart3 size={28} /> {t("menu_reports")}</h1>
          <p className="cell-sub" style={{ margin: "4px 0 0" }}>{t("rep_page_desc")}</p>
        </div>
        <div className="heading-actions" style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
          {tab === "comparison" && backendEnabled() && (
            <Button variant="outline" onClick={exportRequirementCsv}><FileSpreadsheet size={16} /> {t("rep_export_requirement_csv")}</Button>
          )}
          <Button variant="outline" onClick={exportCsv} disabled={!rows.length}><FileSpreadsheet size={16} /> {t("rep_export_csv")}</Button>
          <Button variant="primary" onClick={exportPdf} disabled={!rows.length}><Printer size={16} /> {t("rep_export_pdf")}</Button>
        </div>
      </div>

      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 14, margin: "18px 0" }}>
        <div className="filter-tabs" style={{ display: "flex", flexWrap: "wrap", gap: 6, margin: 0 }}>
          {Object.keys(tabs).map(key => (
            <button key={key} className={tab === key ? "active" : ""} onClick={() => setTab(key)}>
              {t(`rep_tab_${key}`)} <em className="tab-count">{data[key].length}</em>
            </button>
          ))}
        </div>
        <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
          <div style={{ position: "relative" }}>
            <Search size={15} style={{ position: "absolute", left: 10, top: 10, color: "var(--muted)" }} />
            <input type="text" className="input-text" placeholder={t("rep_search")} value={search}
              onChange={e => setSearch(e.target.value)} style={{ paddingLeft: 32, height: 36, width: 180 }} />
          </div>
          {current.dept && (
            <select className="input-select" value={dept} onChange={e => setDept(e.target.value)} style={{ height: 36 }}>
              <option value="all">{t("rep_all_departments")}</option>
              {DEPARTMENTS.map(d => <option key={d} value={d}>{tv(d)}</option>)}
            </select>
          )}
        </div>
      </div>

      {!backendEnabled() || failed ? (
        <Card><EmptyState title={t(failed ? "rep_load_failed" : "rep_need_backend")} description={t("rep_need_backend_desc")} /></Card>
      ) : (
        <>
          <div className="stat-grid" style={{ marginBottom: 20 }}>
            {current.kpis.map(k => <StatCard key={k.label} label={t(k.label)} value={k.value(rows)} icon={k.icon} tone={k.tone} />)}
          </div>
          <Card>
            {loading ? <p className="cell-sub">{t("rep_loading")}</p> : rows.length === 0 ? (
              <EmptyState title={t("rep_empty")} description={t(`rep_empty_${tab}`)} />
            ) : (
              <div style={{ overflowX: "auto" }}>
                <table className="data-table" style={{ width: "100%", fontSize: 13 }}>
                  <thead><tr>{current.columns.map(c => <th key={c.label}>{t(c.label)}</th>)}</tr></thead>
                  <tbody>
                    {rows.map((r, i) => (
                      <tr key={rowKey(r, i)}>
                        {current.columns.map(c => <td key={c.label}>{c.cell ? c.cell(r) : c.text(r)}</td>)}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Card>
        </>
      )}
    </div>
  );
}
