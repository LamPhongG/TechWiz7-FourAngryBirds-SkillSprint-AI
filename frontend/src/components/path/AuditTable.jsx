import { Link } from "react-router-dom";
import { Badge } from "../UI";
import { FinalStatusBadge, PathStatusBadge } from "./Badges";
import { useLanguage } from "../../contexts/LanguageContext";
import { formatDateTime } from "../../utils/helpers";

export const AUDIT_ACTIONS = ["generate", "regenerate", "edit", "submit", "resubmit", "comment", "request_changes", "approve", "archive", "delete"];

const ACTION_TONE = {
  generate: "blue", regenerate: "blue", edit: "default", submit: "purple", resubmit: "purple",
  comment: "default", request_changes: "red", approve: "green", archive: "orange", delete: "red",
};

function describe(e, t) {
  const d = e.details;
  if (!d) return null;
  if (e.action === "edit") {
    if (d.op === "move") return t("audit_edit_move", { module: d.module, from: t(`stage_${d.from}`), to: t(`stage_${d.to}`) });
    return t(`audit_edit_${d.op}`, { kind: t(`kind_${d.kind}`), item: d.item });
  }
  if (e.action === "approve") return t("audit_published_to", { list: [d.departments, d.roles].filter(Boolean).join(" · ") });
  if (d.sources) return `${t("ground_truth_source")}: ${d.sources}`;
  if (d.item) return d.item;
  return null;
}

/** Nhật ký thao tác: thời điểm, người, hành động, lộ trình, trạng thái trước/sau, kết quả kiểm định, lý do */
export default function AuditTable({ entries, pathBasePath, showPath = true }) {
  const { t, locale } = useLanguage();
  if (entries.length === 0) return <p className="cell-sub" style={{ padding: 16, textAlign: "center" }}>{t("audit_empty")}</p>;
  return (
    <div className="table-wrap">
      <table className="audit-table">
        <thead>
          <tr>
            <th>{t("col_timestamp")}</th>
            <th>{t("col_actor")}</th>
            <th>{t("col_action")}</th>
            {showPath && <th>{t("col_path")}</th>}
            <th>{t("col_status_change")}</th>
            <th>{t("col_check_result")}</th>
            <th>{t("col_reason")}</th>
          </tr>
        </thead>
        <tbody>
          {entries.map(e => (
            <tr key={e.id}>
              <td style={{ whiteSpace: "nowrap" }}>{formatDateTime(e.timestamp, locale)}<span className="cell-sub">{e.id}</span></td>
              <td><strong>{e.actor_name}</strong><span className="cell-sub">{e.actor_role ? t(`role_${e.actor_role}`) : "—"}</span></td>
              <td><Badge tone={ACTION_TONE[e.action] || "default"}>{t(`audit_action_${e.action}`)}</Badge></td>
              {showPath && (
                <td>
                  {pathBasePath && e.action !== "delete" ? <Link className="link-btn" to={`${pathBasePath}/${e.path_id}`}>{e.path_id}</Link> : e.path_id}
                  <span className="cell-sub">{e.path_title}{e.revision ? ` · r${e.revision}` : ""}</span>
                </td>
              )}
              <td className="status-change">
                {e.status_before ? <PathStatusBadge status={e.status_before} /> : <span className="cell-sub">—</span>}
                {e.status_after !== e.status_before && <>→ {e.status_after ? <PathStatusBadge status={e.status_after} /> : <span className="cell-sub">—</span>}</>}
              </td>
              <td>{e.final_status ? <FinalStatusBadge status={e.final_status} /> : <span className="cell-sub">—</span>}</td>
              <td className="audit-reason">
                {e.reason || (!describe(e, t) && <span className="cell-sub">—</span>)}
                {describe(e, t) && <span className="cell-sub">{describe(e, t)}</span>}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// Xuất CSV để nộp kèm báo cáo hoặc đối chiếu với bảng audit_logs của backend
export function auditToCsv(entries) {
  const cols = ["id", "timestamp", "actor_id", "actor_name", "actor_role", "action", "path_id", "path_title", "revision", "status_before", "status_after", "final_status", "reason"];
  const esc = v => {
    const s = v == null ? "" : String(v);
    return /[",\n\r]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
  };
  return [cols.join(","), ...entries.map(e => cols.map(c => esc(e[c])).join(","))].join("\n");
}
