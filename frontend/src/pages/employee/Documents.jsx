import { useState } from "react";
import { FileText, Eye, Download } from "../../components/Icons";
import { Card, Badge, SectionHeader, SearchInput, EmptyState, Toast } from "../../components/UI";
import { useLanguage } from "../../contexts/LanguageContext";
import { useDocuments, openStoredFile } from "../../contexts/DocumentsContext";
import { formatLocalDate } from "../../utils/helpers";
import { useAuth } from "../../hooks/useAuth";
import { useMyPaths } from "../../hooks/useMyPaths";

export default function Documents() {
  const [query, setQuery] = useState("");
  const [toast, setToast] = useState("");
  const { t, tv, pick, locale } = useLanguage();
  const { activeDocuments: allActive, loading, getFile } = useDocuments();
  const { user } = useAuth();
  const myPaths = useMyPaths();
  // Tài liệu chung toàn công ty, tài liệu của phòng ban mình, và tài liệu nguồn của các lộ trình được giao
  const pathCodes = new Set(myPaths.flatMap(p => p.sources.map(s => s.code)));
  const activeDocuments = allActive.filter(d => d.category !== "Test Case"
    && (d.department === "Company-wide" || d.department === user.department || pathCodes.has(d.code)));
  const q = query.trim().toLowerCase();
  const filtered = activeDocuments.filter(d => !q || [d.code, d.titleEn, d.title, d.fileName].some(v => v?.toLowerCase().includes(q)));

  const open = async (doc, download) => {
    try { await openStoredFile(getFile, doc, { download }); }
    catch (e) { setToast(t("save_failed", { msg: e.message })); }
  };

  return (
    <div>
      <div className="page-heading">
        <div>
          <span className="eyebrow">{tv(user.department)}</span>
          <h1>{t("company_docs_title")}</h1>
          <p>{t("company_docs_desc")}</p>
        </div>
      </div>
      <Card>
        <SectionHeader
          title={t("doc_library")}
          subtitle={t("doc_library_desc")}
          action={<SearchInput value={query} onChange={setQuery} placeholder={t("search_files")} />}
        />
        {!loading && activeDocuments.length === 0 ? (
          <EmptyState title={t("repo_empty_title")} description={t("employee_docs_empty")} />
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr><th>{t("col_document")}</th><th>{t("col_category")}</th><th>{t("col_version")}</th><th>{t("col_effective_date")}</th><th /></tr>
              </thead>
              <tbody>
                {filtered.map(d => (
                  <tr key={d.id}>
                    <td>
                      <div className="table-primary">
                        <span className="file-icon"><FileText size={16} /></span>
                        <div><strong>{d.code} · {pick(d, "title")}</strong><span className="cell-sub">{d.fileName}</span></div>
                      </div>
                    </td>
                    <td>{tv(d.category)}</td>
                    <td><Badge tone="green">v{d.version}</Badge></td>
                    <td>{formatLocalDate(d.effectiveDate, locale, { day: "2-digit", month: "short", year: "numeric" })}</td>
                    <td>
                      <div className="row-actions">
                        {["pdf", "txt", "md", "csv"].includes(d.ext) && <button className="icon-btn" title={t("action_view")} aria-label={t("action_view")} onClick={() => open(d, false)}><Eye size={16} /></button>}
                        <button className="icon-btn" title={t("action_download")} aria-label={t("action_download")} onClick={() => open(d, true)}><Download size={16} /></button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
      <Toast message={toast} onClose={() => setToast("")} />
    </div>
  );
}
