import { useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { ShieldCheck, MessageSquare, CircleCheck, ShieldAlert, ArrowUpRight } from "../../components/Icons";
import { Card, SectionHeader, StatCard, Button } from "../../components/UI";
import { FinalStatusBadge } from "../../components/path/Badges";
import AuditTable from "../../components/path/AuditTable";
import { useLanguage } from "../../contexts/LanguageContext";
import { usePaths } from "../../contexts/PathsContext";
import { useDocuments } from "../../contexts/DocumentsContext";
import { useAuth } from "../../hooks/useAuth";
import { runPathChecks } from "../../utils/pathChecks";
import { formatDateTime } from "../../utils/helpers";

export default function ReviewerDashboard() {
  const navigate = useNavigate();
  const { t, pick, locale } = useLanguage();
  const { user } = useAuth();
  const { paths, auditLog } = usePaths();
  const { documents, chunksByDocId } = useDocuments();

  const queue = useMemo(() => paths.filter(p => p.status === "in_review"), [paths]);
  const checks = useMemo(() => Object.fromEntries(queue.map(p => [p.id, runPathChecks(p, { documents, chunksByDocId })])),
    [queue, documents, chunksByDocId]);
  const myDecisions = auditLog.filter(e => e.actor_id === user.id && ["approve", "request_changes", "archive"].includes(e.action));

  return (
    <div>
      <div className="page-heading">
        <div>
          <span className="eyebrow">{t("role_reviewer")}</span>
          <h1>{t("dashboard_greeting", { name: user.name.split(" ")[0] })}</h1>
          <p>{t("reviewer_dashboard_desc")}</p>
        </div>
      </div>

      <div className="stat-grid">
        <StatCard label={t("path_status_in_review")} value={queue.length} icon={ShieldCheck} tone="orange" />
        <StatCard label={t("needs_manual_review")} value={Object.values(checks).filter(c => c.final_status === "manual_review").length} icon={ShieldAlert} tone="red" />
        <StatCard label={t("path_status_changes_requested")} value={paths.filter(p => p.status === "changes_requested").length} icon={MessageSquare} tone="purple" />
        <StatCard label={t("path_status_published")} value={paths.filter(p => p.status === "published").length} icon={CircleCheck} tone="green" />
      </div>

      <Card style={{ marginBottom: 18 }}>
        <SectionHeader title={t("review_queue_table")} subtitle={t("review_checklist")} action={<Button variant="ghost" onClick={() => navigate("/reviewer/queue")}>{t("view_all")} <ArrowUpRight size={14} /></Button>} />
        {queue.length === 0 ? <p className="cell-sub">{t("review_queue_empty_desc")}</p> : (
          <div className="focus-list">
            {queue.map(p => (
              <button key={p.id} className="focus-item focus-item--button" onClick={() => navigate(`/reviewer/paths/${p.id}`)}>
                <div className="task-dot active"><ShieldCheck size={14} /></div>
                <div><strong>{pick(p, "title")}</strong><span>{p.id} · r{p.revision} · {t("submitted_at", { date: formatDateTime(p.submitted_at, locale) })}</span></div>
                <FinalStatusBadge status={checks[p.id].final_status} />
              </button>
            ))}
          </div>
        )}
      </Card>

      <Card>
        <SectionHeader title={t("my_decisions")} />
        <AuditTable entries={myDecisions.slice(0, 10)} pathBasePath="/reviewer/paths" />
      </Card>
    </div>
  );
}
