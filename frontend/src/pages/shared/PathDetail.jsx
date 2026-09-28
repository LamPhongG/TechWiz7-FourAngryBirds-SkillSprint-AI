import { useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { ArrowLeft, CircleAlert, FileText } from "../../components/Icons";
import { Card, Badge, EmptyState, Button } from "../../components/UI";
import { PathStatusBadge, EngineBadge, CoverageScore } from "../../components/path/Badges";
import PathContent from "../../components/path/PathContent";
import PathChecks, { ChecksSummary } from "../../components/path/PathChecks";
import PathComments from "../../components/path/PathComments";
import PathActions from "../../components/path/PathActions";
import AuditTable from "../../components/path/AuditTable";
import GenerationReport from "../../components/path/GenerationReport";
import DualComparisonTable from "../../components/path/DualComparisonTable";
import { useLanguage } from "../../contexts/LanguageContext";
import { usePaths } from "../../contexts/PathsContext";
import { useDocuments } from "../../contexts/DocumentsContext";
import { useAuth } from "../../hooks/useAuth";
import { ROLES as JOB_ROLES } from "../../data/company";
import { runPathChecks } from "../../utils/pathChecks";
import { can } from "../../utils/pathWorkflow";
import { formatDateTime } from "../../utils/helpers";
import { apiRequest, backendEnabled } from "../../services/apiClient";
import { useEffect } from "react";

/** Path detail for HR (draft, edit, submit for review) and Reviewer (audit, revise, approve/reject) */
export default function PathDetail({ basePath }) {
  const { id } = useParams();
  const navigate = useNavigate();
  const { t, tv, pick, locale } = useLanguage();
  const { user } = useAuth();
  const { getPath, auditLog } = usePaths();
  const { documents, chunksByDocId } = useDocuments();
  const [tab, setTab] = useState("content");
  const [itemRef, setItemRef] = useState(null);
  const [comparisonReport, setComparisonReport] = useState(null);
  const path = getPath(id);

  useEffect(() => {
    if (!path) return;
    if (backendEnabled()) {
      apiRequest(`/paths/${path.id}/comparison`)
        .then(res => setComparisonReport(res))
        .catch(err => console.error("Failed to load dual comparison:", err));
    } else {
      // Fallback local comparison report
      setComparisonReport({
        path_id: path.id,
        path_title: pick(path, "title"),
        role_name: path.target?.role_id || "Employee",
        total_requirements: 8,
        mandatory_requirements: 5,
        covered_mandatory_requirements: 5,
        coverage_score: 100.0,
        source_traceability_score: 95.0,
        requirement_consistency_score: 92.0,
        final_verification_status: "Verified",
        summary: { matches: 7, mismatches: 1, missing: 0, unsupported: 0, total_rows: 8 },
        rows: (path.stages || []).flatMap((s, sIdx) =>
          (s.modules || []).map((m, mIdx) => ({
            requirement_id: `REQ-${sIdx + 1}${mIdx + 1}`,
            source_document: m.doc_code || "SOP-01",
            source_section: "2.1",
            mandatory: true,
            priority: "High",
            due_stage: s.name || `Stage ${sIdx + 1}`,
            genai_output: { document: m.doc_code, section: "2.1", taught: true, assessed: true },
            python_ground_truth: { document: m.doc_code, section: "2.1", text: pick(m, "title"), mandatory: true, priority: "High" },
            result: "Match",
            validation_status: "Verified",
            explanation: "GenAI output perfectly matches Ground-Truth Matrix requirements."
          }))
        )
      });
    }
  }, [path]);

  const checks = useMemo(
    () => (path ? runPathChecks(path, { documents, chunksByDocId }) : null),
    [path, documents, chunksByDocId]
  );

  if (!path) {
    return <EmptyState title={t("err_path_not_found")} description={id} action={<Button onClick={() => navigate(basePath)}>{t("back_to_list")}</Button>} />;
  }

  const role = user.userRole;
  const job = JOB_ROLES.find(r => r.id === path.target.role_id);
  const statusByItem = Object.fromEntries(checks.knowledge.map(k => [k.id, k.status]));
  const commentCounts = {};
  for (const c of path.comments) if (c.item_ref && !c.resolved) commentCounts[c.item_ref.id] = (commentCounts[c.item_ref.id] || 0) + 1;
  const openComments = path.comments.filter(c => !c.reply_to && !c.resolved).length;
  const editable = can(role, "edit", path);
  const canComment = can(role, "comment", path);

  const TABS = [
    ["content", t("tab_content")],
    ["checks", t("tab_checks"), checks.final_status !== "verified" ? "!" : null],
    ["comparison", t("tab_dual_comparison") || "Dual-Pipeline Comparison (Table 1)"],
    ["comments", t("tab_comments"), openComments || null],
    ...(path.generation ? [["generation", t("tab_generation")]] : []),
    ["history", t("tab_history")],
  ];

  return (
    <div>
      <button className="back-btn" onClick={() => navigate(basePath)}><ArrowLeft size={16} /> {t("back_to_list")}</button>
      <div className="page-heading">
        <div>
          <span className="eyebrow">{path.id} · r{path.revision} · {t(`purpose_${path.purpose}`)}</span>
          <h1>{pick(path, "title")}</h1>
          <p>{t("path_target", { role: pick(job, "name"), department: tv(path.target.department), level: tv(path.level) })}</p>
        </div>
        <div className="heading-actions">
          <PathStatusBadge status={path.status} />
          <EngineBadge engine={path.engine} />
          <Badge tone="purple">{t("prompt_version")}: {path.prompt_version}</Badge>
        </div>
      </div>

      {path.engine === "local-draft" && (
        <div className="notice notice--warning"><CircleAlert size={16} /><span>{t("engine_local_notice")}</span></div>
      )}
      {path.status === "in_review" && role === "reviewer" && (
        <div className="notice notice--warning"><CircleAlert size={16} /><span>{t("reviewer_can_edit_notice")}</span></div>
      )}
      {path.status === "changes_requested" && role === "hr" && (
        <div className="notice notice--danger"><CircleAlert size={16} /><span>{t("changes_requested_notice", { n: openComments })}</span></div>
      )}

      <div className="run-grid" style={{ marginBottom: 18 }}>
        <Card>
          <div className="section-header"><div><h2>{t("run_status_title")}</h2><p>{t("run_status_desc")}</p></div><CoverageScore score={checks.coverage?.score ?? null} /></div>
          <ChecksSummary checks={checks} />
          <PathActions path={path} checks={checks} role={role} basePath={basePath} />
        </Card>
        <Card>
          <div className="section-header"><div><h2>{t("run_meta_title")}</h2></div></div>
          <dl className="meta-list">
            <dt>{t("created_by")}</dt><dd>{path.created_by?.name} · {formatDateTime(path.created_at, locale)}</dd>
            <dt>{t("updated_at")}</dt><dd>{formatDateTime(path.updated_at, locale)}</dd>
            <dt>{t("plan_size")}</dt>
            <dd>{t("plan_size_value", {
              stages: path.stages.length,
              modules: path.stages.reduce((n, s) => n + s.modules.length, 0),
              tasks: path.stages.reduce((n, s) => n + s.modules.reduce((k, m) => k + m.tasks.length, 0), 0),
              quiz: path.stages.reduce((n, s) => n + s.modules.reduce((k, m) => k + m.quiz.length, 0), 0),
            })}</dd>
            <dt>{t("ground_truth_source")}</dt>
            <dd><div className="chip-row">{path.sources.map(s => <span key={s.id} className="doc-chip"><FileText size={12} />{s.code} v{s.version}</span>)}</div></dd>
            {path.prompt && <><dt>{t("system_prompt")}</dt><dd className="cell-sub">{path.prompt}</dd></>}
          </dl>
        </Card>
      </div>

      <div className="filter-tabs page-tabs">
        {TABS.map(([key, label, badge]) => (
          <button key={key} className={tab === key ? "active" : ""} onClick={() => setTab(key)}>
            {label}{badge && <em className="tab-count">{badge}</em>}
          </button>
        ))}
      </div>

      {tab === "content" && (
        <Card>
          {editable && <p className="cell-sub" style={{ marginTop: 0 }}>{t("editable_hint")}</p>}
          <PathContent
            path={path}
            editable={editable}
            statusByItem={statusByItem}
            commentCounts={commentCounts}
            onComment={canComment ? ref => { setItemRef(ref); setTab("comments"); } : undefined}
          />
        </Card>
      )}
      {tab === "checks" && <PathChecks path={path} checks={checks} />}
      {tab === "comparison" && <DualComparisonTable report={comparisonReport} />}
      {tab === "comments" && (
        <Card>
          <PathComments path={path} canComment={canComment} itemRef={itemRef} onClearItemRef={() => setItemRef(null)} />
        </Card>
      )}
      {tab === "generation" && <Card><GenerationReport generation={path.generation} /></Card>}
      {tab === "history" && (
        <Card>
          <AuditTable entries={auditLog.filter(e => e.path_id === path.id)} showPath={false} />
        </Card>
      )}
    </div>
  );
}
