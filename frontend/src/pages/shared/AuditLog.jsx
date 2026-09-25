import { useState } from "react";
import { Download } from "../../components/Icons";
import { Card, SectionHeader, Button, SearchInput } from "../../components/UI";
import AuditTable, { AUDIT_ACTIONS, auditToCsv } from "../../components/path/AuditTable";
import { useLanguage } from "../../contexts/LanguageContext";
import { usePaths } from "../../contexts/PathsContext";
import { todayISO } from "../../utils/helpers";

/** Nhật ký kiểm toán: mọi lần sinh, sửa, gửi duyệt, góp ý, duyệt, thu hồi — chỉ đọc */
export default function AuditLog({ pathBasePath }) {
  const { t } = useLanguage();
  const { auditLog } = usePaths();
  const [action, setAction] = useState("");
  const [query, setQuery] = useState("");

  const q = query.trim().toLowerCase();
  const rows = auditLog
    .filter(e => !action || e.action === action)
    .filter(e => !q || [e.path_id, e.path_title, e.actor_name, e.reason].some(v => v?.toLowerCase().includes(q)));

  const exportCsv = () => {
    const blob = new Blob([`﻿${auditToCsv(rows)}`], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `audit_log_${todayISO()}.csv`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  };

  return (
    <div>
      <div className="page-heading">
        <div>
          <span className="eyebrow">{t("audit_eyebrow")}</span>
          <h1>{t("menu_audit_log")}</h1>
          <p>{t("audit_desc")}</p>
        </div>
        <Button variant="secondary" onClick={exportCsv} disabled={rows.length === 0} icon={<Download size={16} />}>{t("export_as", { format: "CSV" })}</Button>
      </div>
      <Card>
        <SectionHeader
          title={t("audit_count", { n: rows.length })}
          subtitle={t("audit_immutable")}
          action={<SearchInput value={query} onChange={setQuery} placeholder={t("search_audit")} />}
        />
        <div className="toolbar" style={{ justifyContent: "flex-start" }}>
          <select className="filter-select" value={action} onChange={e => setAction(e.target.value)}>
            <option value="">{t("filter_action_all")}</option>
            {AUDIT_ACTIONS.map(a => <option key={a} value={a}>{t(`audit_action_${a}`)}</option>)}
          </select>
        </div>
        <AuditTable entries={rows} pathBasePath={pathBasePath} />
      </Card>
    </div>
  );
}
