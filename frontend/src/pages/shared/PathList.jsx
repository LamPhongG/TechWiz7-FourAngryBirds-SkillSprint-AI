import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowUpRight, WandSparkles } from "../../components/Icons";
import { Card, SectionHeader, Button, SearchInput, EmptyState } from "../../components/UI";
import { PathStatusBadge, FinalStatusBadge, CoverageScore } from "../../components/path/Badges";
import { useLanguage } from "../../contexts/LanguageContext";
import { usePaths } from "../../contexts/PathsContext";
import { useDocuments } from "../../contexts/DocumentsContext";
import { ROLES as JOB_ROLES } from "../../data/company";
import { runPathChecks } from "../../utils/pathChecks";
import { formatDateTime } from "../../utils/helpers";

/**
 * Danh sách lộ trình theo trạng thái. HR xem mọi lộ trình mình tạo; Reviewer dùng cùng trang
 * với bộ lọc mặc định khác (hàng đợi = đang chờ duyệt).
 */
export default function PathList({ basePath, tabs, defaultTab, eyebrow, title, description, createPath }) {
  const navigate = useNavigate();
  const { t, tv, pick, locale } = useLanguage();
  const { paths } = usePaths();
  const { documents, chunksByDocId } = useDocuments();
  const [tab, setTab] = useState(defaultTab || tabs[0]);
  const [query, setQuery] = useState("");

  const checks = useMemo(() => Object.fromEntries(paths.map(p => [p.id, runPathChecks(p, { documents, chunksByDocId })])),
    [paths, documents, chunksByDocId]);

  const visible = paths.filter(p => tabs.includes(p.status) || tabs.includes("all"));
  const count = key => (key === "all" ? visible.length : visible.filter(p => p.status === key).length);
  const q = query.trim().toLowerCase();
  const rows = visible
    .filter(p => tab === "all" || p.status === tab)
    .filter(p => !q || [p.id, p.title, p.titleEn, ...p.sources.map(s => s.code)].some(v => v?.toLowerCase().includes(q)));

  return (
    <div>
      <div className="page-heading">
        <div>
          <span className="eyebrow">{eyebrow}</span>
          <h1>{title}</h1>
          <p>{description}</p>
        </div>
        {createPath && <Button onClick={() => navigate(createPath)} icon={<WandSparkles size={16} />}>{t("menu_create_path")}</Button>}
      </div>

      <Card>
        <SectionHeader title={t("paths_count", { n: rows.length })} action={<SearchInput value={query} onChange={setQuery} placeholder={t("search_paths")} />} />
        {tabs.length > 1 && (
          <div className="filter-tabs" style={{ marginBottom: 12, flexWrap: "wrap" }}>
            {tabs.map(k => (
              <button key={k} className={tab === k ? "active" : ""} onClick={() => setTab(k)}>
                {k === "all" ? t("filter_all") : t(`path_status_${k}`)} ({count(k)})
              </button>
            ))}
          </div>
        )}
        {visible.length === 0 ? (
          <EmptyState title={t("paths_empty")} description={t("paths_empty_desc")}
            action={createPath && <Button onClick={() => navigate(createPath)} icon={<WandSparkles size={16} />}>{t("menu_create_path")}</Button>} />
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>{t("col_path")}</th>
                  <th>{t("col_target")}</th>
                  <th>{t("col_status")}</th>
                  <th>{t("col_check_result")}</th>
                  <th>{t("coverage_short")}</th>
                  <th>{t("col_updated")}</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {rows.length === 0 ? (
                  <tr><td colSpan={7} style={{ textAlign: "center", color: "var(--muted)", padding: 24 }}>{t("repo_no_match")}</td></tr>
                ) : rows.map(p => {
                  const job = JOB_ROLES.find(r => r.id === p.target.role_id);
                  const c = checks[p.id];
                  const open = p.comments.filter(x => !x.reply_to && !x.resolved).length;
                  return (
                    <tr key={p.id} style={{ cursor: "pointer" }} onClick={() => navigate(`${basePath}/${p.id}`)}>
                      <td>
                        <strong>{pick(p, "title")}</strong>
                        <span className="cell-sub">{p.id} · r{p.revision} · {t(`purpose_${p.purpose}`)} · {tv(p.level)}</span>
                      </td>
                      <td>{pick(job, "name")}<span className="cell-sub">{tv(p.target.department)}</span></td>
                      <td>
                        <PathStatusBadge status={p.status} />
                        {open > 0 && <span className="cell-sub text-danger">{t("open_comments_n", { n: open })}</span>}
                      </td>
                      <td><FinalStatusBadge status={c.final_status} /></td>
                      <td><CoverageScore score={c.coverage?.score ?? null} /></td>
                      <td style={{ whiteSpace: "nowrap" }}>{formatDateTime(p.updated_at, locale)}</td>
                      <td><Button variant="ghost" onClick={e => { e.stopPropagation(); navigate(`${basePath}/${p.id}`); }}>{t("open")} <ArrowUpRight size={14} /></Button></td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}
