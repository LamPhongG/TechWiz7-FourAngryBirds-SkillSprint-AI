import { useNavigate } from "react-router-dom";
import { FileText, Layers3, ShieldAlert, CircleCheck, ArrowUpRight, WandSparkles, Upload, CircleAlert, MessageSquare } from "../../components/Icons";
import { Card, SectionHeader, StatCard, Button, Badge } from "../../components/UI";
import { PathStatusBadge } from "../../components/path/Badges";
import { useLanguage } from "../../contexts/LanguageContext";
import { useDocuments } from "../../contexts/DocumentsContext";
import { usePaths } from "../../contexts/PathsContext";
import { useAuth } from "../../hooks/useAuth";
import { DEPARTMENTS } from "../../data/company";

export default function HrDashboard() {
  const navigate = useNavigate();
  const { t, tv, pick } = useLanguage();
  const { user } = useAuth();
  const { documents, activeDocuments } = useDocuments();
  const { paths } = usePaths();

  const processedCount = activeDocuments.filter(d => d.processing === "done").length;
  const problemDocs = documents.filter(d => d.processing === "failed" || d.injectionFlagCount > 0);
  const byStatus = s => paths.filter(p => p.status === s);
  const published = byStatus("published");

  const todo = [
    ...byStatus("changes_requested").map(p => ({ key: p.id, icon: MessageSquare, tone: "red", text: t("todo_changes_requested", { title: pick(p, "title"), n: p.comments.filter(c => !c.reply_to && !c.resolved).length }), to: `/hr/paths/${p.id}` })),
    ...byStatus("draft").map(p => ({ key: p.id, icon: Layers3, tone: "default", text: t("todo_draft", { title: pick(p, "title") }), to: `/hr/paths/${p.id}` })),
    ...problemDocs.map(d => ({ key: d.id, icon: d.injectionFlagCount ? ShieldAlert : CircleAlert, tone: "orange", text: t(d.injectionFlagCount ? "todo_doc_flagged" : "todo_doc_failed", { code: d.code, version: d.version }), to: "/hr/documents" })),
  ];

  return (
    <div>
      <div className="page-heading">
        <div>
          <span className="eyebrow">{t("role_hr")}</span>
          <h1>{t("dashboard_greeting", { name: user.name.split(" ")[0] })}</h1>
          <p>{t("hr_dashboard_desc")}</p>
        </div>
        <div className="heading-actions">
          <Button variant="secondary" onClick={() => navigate("/hr/documents")} icon={<Upload size={16} />}>{t("upload_documents")}</Button>
          <Button onClick={() => navigate("/hr/paths/new")} icon={<WandSparkles size={16} />}>{t("menu_create_path")}</Button>
        </div>
      </div>

      <div className="stat-grid">
        <StatCard label={t("stat_docs_ready")} value={`${processedCount} / ${activeDocuments.length}`} icon={FileText} tone="blue" />
        <StatCard label={t("path_status_in_review")} value={byStatus("in_review").length} icon={Layers3} tone="orange" />
        <StatCard label={t("path_status_changes_requested")} value={byStatus("changes_requested").length} icon={MessageSquare} tone="red" />
        <StatCard label={t("path_status_published")} value={published.length} icon={CircleCheck} tone="green" />
      </div>

      <div className="dashboard-grid">
        <Card>
          <SectionHeader title={t("todo_title")} subtitle={t("todo_desc")} />
          {todo.length === 0 ? <p className="cell-sub">{t("todo_empty")}</p> : (
            <div className="focus-list">
              {todo.map(item => (
                <button key={item.key} className="focus-item focus-item--button" onClick={() => navigate(item.to)}>
                  <div className={`task-dot ${item.tone === "red" ? "active" : ""}`}><item.icon size={14} /></div>
                  <div><strong>{item.text}</strong></div>
                  <ArrowUpRight size={16} />
                </button>
              ))}
            </div>
          )}
        </Card>
        <Card>
          <SectionHeader title={t("published_by_department")} subtitle={t("published_by_department_desc")} />
          {published.length === 0 ? <p className="cell-sub">{t("no_published_paths")}</p> : (
            <ul className="dept-list">
              {DEPARTMENTS.map(d => {
                const list = published.filter(p => p.published_to.departments.includes(d));
                if (!list.length) return null;
                return (
                  <li key={d}>
                    <strong>{tv(d)}</strong>
                    <span>{list.map(p => <Badge key={p.id} tone="green">{pick(p, "title")}</Badge>)}</span>
                  </li>
                );
              })}
            </ul>
          )}
        </Card>
      </div>

      <Card>
        <SectionHeader title={t("recent_paths")} action={<Button variant="ghost" onClick={() => navigate("/hr/paths")}>{t("view_all")} <ArrowUpRight size={14} /></Button>} />
        {paths.length === 0 ? <p className="cell-sub">{t("paths_empty_desc")}</p> : (
          <div className="focus-list">
            {paths.slice(0, 5).map(p => (
              <button key={p.id} className="focus-item focus-item--button" onClick={() => navigate(`/hr/paths/${p.id}`)}>
                <div className="task-dot"><Layers3 size={14} /></div>
                <div><strong>{pick(p, "title")}</strong><span>{p.id} · r{p.revision}</span></div>
                <PathStatusBadge status={p.status} />
              </button>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}
