import { useEffect, useRef, useState } from "react";
import { FileText, Upload, Database, Eye, Download, Trash2, CircleAlert, CircleCheck, Loader2, Plus, X, ShieldCheck, ShieldAlert, Layers3 } from "../../components/Icons";
import { Card, Badge, SectionHeader, Button, SearchInput, Modal, Toast, EmptyState, ProgressBar } from "../../components/UI";
import { SkeletonTableRows } from "../../components/SkeletonLoader";
import { ProcessingCell, ChunksModal } from "../../components/DocumentProcessing";
import { useLanguage } from "../../contexts/LanguageContext";
import { useDocuments, openStoredFile } from "../../contexts/DocumentsContext";
import { useAuth } from "../../hooks/useAuth";
import { company, DOCUMENT_CATALOG, DOCUMENT_CATEGORIES, DEPARTMENTS, UPLOAD_RULES } from "../../data/company";
import { buildDraft, findCatalogEntry, formatFileSize, hashFile, inspectContent, validateDraft } from "../../utils/documentValidation";
import { formatLocalDate, todayISO } from "../../utils/helpers";

const LIFECYCLE_TONE = { active: "green", obsolete: "default", expired: "red", upcoming: "blue" };
const STATUS_FILTERS = ["all", "active", "obsolete", "expired", "upcoming"];
const PREVIEWABLE = ["pdf", "txt", "md", "csv"];
const PREVIEW_LIMIT = 20000;

export default function AdminDocuments() {
  const { t, tv, pick, locale } = useLanguage();
  const { documents, loading, error, removeDocument, getFile } = useDocuments();
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState("");
  const [department, setDepartment] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [uploadOpen, setUploadOpen] = useState(false);
  const [preview, setPreview] = useState(null);
  const [toDelete, setToDelete] = useState(null);
  const [chunksDoc, setChunksDoc] = useState(null);
  const [toast, setToast] = useState("");

  const dateOpts = { day: "2-digit", month: "short", year: "numeric" };
  const q = query.trim().toLowerCase();
  const filtered = documents.filter(d =>
    (!q || [d.code, d.titleEn, d.title, d.fileName].some(v => v?.toLowerCase().includes(q)))
    && (!category || d.category === category)
    && (!department || d.department === department)
    && (statusFilter === "all" || d.status === statusFilter)
  );

  const uploadedCodes = new Set(documents.map(d => d.code));
  const coveredCount = DOCUMENT_CATALOG.filter(c => uploadedCodes.has(c.code)).length;
  const activeCount = documents.filter(d => d.status === "active").length;
  const totalSize = documents.reduce((sum, d) => sum + (d.size || 0), 0);
  const flaggedDocs = documents.filter(d => d.injectionFlagCount > 0);

  const handlePreview = async (doc) => {
    try {
      if (doc.ext === "pdf") return await openStoredFile(getFile, doc);
      const blob = await getFile(doc.id);
      const text = blob ? await blob.text() : "";
      setPreview({ doc, text: text.slice(0, PREVIEW_LIMIT), truncated: text.length > PREVIEW_LIMIT });
    } catch (e) {
      setToast(t("save_failed", { msg: e.message }));
    }
  };

  const handleDownload = async (doc) => {
    try { await openStoredFile(getFile, doc, { download: true }); }
    catch (e) { setToast(t("save_failed", { msg: e.message })); }
  };

  const confirmDelete = async () => {
    try {
      await removeDocument(toDelete.id);
      setToast(t("doc_deleted"));
    } catch (e) {
      setToast(t("save_failed", { msg: e.message }));
    }
    setToDelete(null);
  };

  return (
    <div>
      <div className="page-heading">
        <div>
          <span className="eyebrow">{t("doc_repo_eyebrow")}</span>
          <h1>{t("doc_repo_title")}</h1>
          <p>{t("doc_repo_desc")}</p>
        </div>
        <Button onClick={() => setUploadOpen(true)} disabled={!!error} icon={<Upload size={16} />}>{t("upload_documents")}</Button>
      </div>

      {error && (
        <div className="notice notice--danger"><CircleAlert size={16} /><span>{t("storage_unavailable")}</span></div>
      )}

      {flaggedDocs.length > 0 && (
        <div className="notice notice--danger">
          <ShieldAlert size={16} />
          <span>
            {t("injection_repo_warning", { n: flaggedDocs.length })}{" "}
            {flaggedDocs.map((d, i) => (
              <span key={d.id}>{i > 0 && ", "}<button type="button" className="link-btn" onClick={() => setChunksDoc(d)}>{d.code} v{d.version}</button></span>
            ))}
          </span>
        </div>
      )}

      <div className="stat-grid">
        <Card className="mini-stat"><Database size={20} /><div><strong>{documents.length}</strong><span>{t("stat_docs_total")}</span></div></Card>
        <Card className="mini-stat"><ShieldCheck size={20} /><div><strong>{activeCount}</strong><span>{t("stat_docs_active")}</span></div></Card>
        <Card className="mini-stat"><Layers3 size={20} /><div><strong>{coveredCount} / {DOCUMENT_CATALOG.length}</strong><span>{t("stat_catalog_coverage")}</span></div></Card>
        <Card className="mini-stat"><FileText size={20} /><div><strong>{formatFileSize(totalSize)}</strong><span>{t("stat_storage")}</span></div></Card>
      </div>

      <Card style={{ marginBottom: 18 }}>
        <SectionHeader title={t("catalog_title")} subtitle={t("catalog_desc", { company: company.shortName })} />
        <ProgressBar value={Math.round((coveredCount / DOCUMENT_CATALOG.length) * 100)} showValue />
        <div className="catalog-grid">
          {DOCUMENT_CATALOG.map(c => {
            const has = uploadedCodes.has(c.code);
            return (
              <div key={c.code} className={`catalog-chip ${has ? "catalog-chip--done" : ""}`} title={`${pick(c, "title")} · ${tv(c.category)}`}>
                {has ? <CircleCheck size={14} /> : <CircleAlert size={14} />}
                <strong>{c.code}</strong>
                <span>{pick(c, "title")}</span>
              </div>
            );
          })}
        </div>
      </Card>

      <Card>
        <SectionHeader
          title={t("repo_table_title")}
          subtitle={t("repo_table_desc", { n: documents.length })}
          action={<SearchInput value={query} onChange={setQuery} placeholder={t("search_doc_placeholder")} />}
        />
        <div className="toolbar" style={{ justifyContent: "flex-start", flexWrap: "wrap" }}>
          <div className="filter-tabs">
            {STATUS_FILTERS.map(s => (
              <button key={s} className={statusFilter === s ? "active" : ""} onClick={() => setStatusFilter(s)}>
                {s === "all" ? t("filter_all") : t(`doc_${s}`)}
              </button>
            ))}
          </div>
          <select className="filter-select" value={category} onChange={e => setCategory(e.target.value)}>
            <option value="">{t("filter_category_all")}</option>
            {DOCUMENT_CATEGORIES.map(c => <option key={c} value={c}>{tv(c)}</option>)}
          </select>
          <select className="filter-select" value={department} onChange={e => setDepartment(e.target.value)}>
            <option value="">{t("filter_department_all")}</option>
            {DEPARTMENTS.map(d => <option key={d} value={d}>{tv(d)}</option>)}
          </select>
        </div>

        {!loading && documents.length === 0 ? (
          <EmptyState
            title={t("repo_empty_title")}
            description={t("repo_empty_desc")}
            action={!error && <Button onClick={() => setUploadOpen(true)} icon={<Upload size={16} />}>{t("upload_documents")}</Button>}
          />
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>{t("col_document")}</th>
                  <th>{t("col_category")}</th>
                  <th>{t("col_department")}</th>
                  <th>{t("col_version")}</th>
                  <th>{t("col_validity")}</th>
                  <th>{t("col_lifecycle")}</th>
                  <th>{t("col_processing")}</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {loading ? <SkeletonTableRows rows={4} cols={8} /> : filtered.length === 0 ? (
                  <tr><td colSpan={8} style={{ textAlign: "center", color: "var(--muted)", padding: 24 }}>{t("repo_no_match")}</td></tr>
                ) : filtered.map(d => (
                  <tr key={d.id}>
                    <td>
                      <div className="table-primary">
                        <span className="file-icon"><FileText size={16} /></span>
                        <div>
                          <strong>{d.code} · {pick(d, "title")}</strong>
                          <span className="cell-sub">{d.fileName} · {formatFileSize(d.size)}</span>
                          <span className="cell-sub">{t("uploaded_by_on", { name: d.uploadedBy || "—", date: formatLocalDate(d.uploadedAt.slice(0, 10), locale, dateOpts) })}</span>
                        </div>
                      </div>
                    </td>
                    <td>{tv(d.category)}</td>
                    <td>{tv(d.department)}</td>
                    <td><Badge tone="default">v{d.version}</Badge></td>
                    <td>
                      <span style={{ display: "block" }}>{formatLocalDate(d.effectiveDate, locale, dateOpts)}</span>
                      <span className="cell-sub">{d.expiryDate ? formatLocalDate(d.expiryDate, locale, dateOpts) : t("no_expiry")}</span>
                    </td>
                    <td>
                      <Badge tone={LIFECYCLE_TONE[d.status]}>{t(`doc_${d.status}`)}</Badge>
                      {d.supersededBy && <span className="cell-sub">{t("superseded_by", { version: d.supersededBy.version })}</span>}
                    </td>
                    <td><ProcessingCell doc={d} onOpenChunks={setChunksDoc} /></td>
                    <td>
                      <div className="row-actions">
                        {PREVIEWABLE.includes(d.ext) && (
                          <button className="icon-btn" title={t("action_view")} aria-label={t("action_view")} onClick={() => handlePreview(d)}><Eye size={16} /></button>
                        )}
                        <button className="icon-btn" title={t("action_download")} aria-label={t("action_download")} onClick={() => handleDownload(d)}><Download size={16} /></button>
                        <button className="icon-btn" title={t("action_delete")} aria-label={t("action_delete")} onClick={() => setToDelete(d)}><Trash2 size={16} /></button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {uploadOpen && (
        <UploadModal
          onClose={() => setUploadOpen(false)}
          onSaved={n => setToast(t("docs_saved", { n }))}
        />
      )}

      <Modal open={!!preview} title={preview ? t("preview_title", { name: preview.doc.fileName }) : ""} onClose={() => setPreview(null)} width="900px">
        {preview && (
          <>
            {preview.truncated && <p className="cell-sub" style={{ marginBottom: 8 }}>{t("preview_truncated", { n: PREVIEW_LIMIT.toLocaleString(locale) })}</p>}
            <pre className="doc-preview">{preview.text}</pre>
          </>
        )}
      </Modal>

      <ChunksModal doc={chunksDoc} onClose={() => setChunksDoc(null)} />

      <Modal open={!!toDelete} title={t("delete_title")} onClose={() => setToDelete(null)}>
        {toDelete && (
          <>
            <p>{t("delete_desc", { code: toDelete.code, version: toDelete.version, file: toDelete.fileName })}</p>
            {toDelete.status === "active" && <div className="notice notice--warning"><CircleAlert size={16} /><span>{t("delete_active_warn")}</span></div>}
            <div className="modal-actions">
              <Button variant="secondary" onClick={() => setToDelete(null)}>{t("cancel")}</Button>
              <Button className="btn btn-danger" onClick={confirmDelete} icon={<Trash2 size={15} />}>{t("action_delete")}</Button>
            </div>
          </>
        )}
      </Modal>

      <Toast message={toast} onClose={() => setToast("")} />
    </div>
  );
}

// Modal tải lên: chọn nhiều file → kiểm tra & chỉnh metadata → lưu các file hợp lệ
function UploadModal({ onClose, onSaved }) {
  const { t, tv, locale } = useLanguage();
  const { user } = useAuth();
  const { documents, addDocuments } = useDocuments();
  const [drafts, setDrafts] = useState([]);
  const [dragging, setDragging] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState("");
  const inputRef = useRef(null);
  const mounted = useRef(true);
  const today = todayISO();

  // StrictMode (dev) unmount rồi mount lại component — phải bật lại cờ ở mỗi lần mount
  useEffect(() => {
    mounted.current = true;
    return () => { mounted.current = false; };
  }, []);

  const updateDraft = (key, patch) => setDrafts(list => list.map(d => (d.key === key ? { ...d, ...patch } : d)));

  const addFiles = (fileList) => {
    const newDrafts = Array.from(fileList).map(file => buildDraft(file, { today }));
    setDrafts(list => [...list, ...newDrafts]);
    // Băm và đọc nội dung song song; kết quả điền vào từng dòng khi xong
    newDrafts.forEach(async (draft) => {
      const [hash, contentIssues] = await Promise.all([
        hashFile(draft.file).catch(() => ""),
        inspectContent(draft.file, draft.ext).catch(() => [{ key: "err_file_unreadable" }]),
      ]);
      if (mounted.current) updateDraft(draft.key, { hash, contentIssues });
    });
  };

  const changeCode = (draft, value) => {
    const patch = { code: value };
    const entry = findCatalogEntry(value);
    // Mã có trong danh mục → tự điền những ô còn trống
    if (entry) {
      if (!draft.category) patch.category = entry.category;
      if (!draft.department) patch.department = entry.department;
      if (!draft.titleEn.trim()) patch.titleEn = entry.titleEn.replace(/\s*\(obsolete\)$/i, "");
    }
    updateDraft(draft.key, patch);
  };

  const results = drafts.map(d => ({ draft: d, ...validateDraft(d, { existing: documents, batch: drafts, today }) }));
  const validDrafts = results.filter(r => r.valid).map(r => r.draft);
  const invalidCount = results.filter(r => !r.pending && !r.valid).length;
  const pendingCount = results.filter(r => r.pending).length;

  const save = async () => {
    setSaving(true);
    setSaveError("");
    try {
      const n = await addDocuments(validDrafts, user?.name);
      onSaved(n);
      const savedKeys = new Set(validDrafts.map(d => d.key));
      const remaining = drafts.filter(d => !savedKeys.has(d.key));
      if (remaining.length === 0) onClose();
      else setDrafts(remaining);
    } catch (e) {
      setSaveError(t("save_failed", { msg: e.message }));
    } finally {
      setSaving(false);
    }
  };

  // Đóng modal khi đang có file chưa lưu thì hỏi lại, tránh mất công nhập metadata
  const requestClose = () => {
    if (saving) return;
    if (drafts.length && !window.confirm(t("discard_uploads"))) return;
    onClose();
  };

  const onDrop = (e) => {
    e.preventDefault();
    setDragging(false);
    if (e.dataTransfer.files?.length) addFiles(e.dataTransfer.files);
  };

  return (
    <Modal open title={t("upload_modal_title")} onClose={requestClose} width="1180px">
      <div
        className={`upload-zone ${dragging ? "upload-zone--active" : ""} ${drafts.length ? "upload-zone--compact" : ""}`}
        onDragEnter={e => { e.preventDefault(); setDragging(true); }}
        onDragOver={e => { e.preventDefault(); setDragging(true); }}
        onDragLeave={e => { e.preventDefault(); setDragging(false); }}
        onDrop={onDrop}
        onClick={() => inputRef.current?.click()}
        role="button"
        tabIndex={0}
        onKeyDown={e => { if (e.key === "Enter" || e.key === " ") inputRef.current?.click(); }}
      >
        {drafts.length ? <Plus size={18} /> : <Upload size={30} />}
        <h3>{drafts.length ? t("add_more_files") : t("upload_drop_title")}</h3>
        {!drafts.length && (
          <>
            <p>{t("upload_drop_desc", { max: UPLOAD_RULES.maxSizeMB })}</p>
            <p className="cell-sub">{t("upload_drop_hint")}</p>
          </>
        )}
        <input
          ref={inputRef}
          type="file"
          multiple
          accept={UPLOAD_RULES.allowedExtensions.map(e => `.${e}`).join(",")}
          onChange={e => { if (e.target.files?.length) addFiles(e.target.files); e.target.value = ""; }}
          style={{ display: "none" }}
        />
      </div>

      {drafts.length > 0 && (
        <>
          <div className="upload-review-head">
            <h4>{t("upload_review_title", { n: drafts.length })}</h4>
            <span className="cell-sub">{t("upload_summary", { valid: validDrafts.length, invalid: invalidCount, pending: pendingCount })}</span>
          </div>
          <div className="table-wrap">
            <table className="upload-table">
              <thead>
                <tr>
                  <th>{t("col_file")}</th>
                  <th>{t("col_code")}</th>
                  <th>{t("col_title")}</th>
                  <th>{t("col_category")}</th>
                  <th>{t("col_department")}</th>
                  <th>{t("col_version")}</th>
                  <th>{t("col_effective_date")}</th>
                  <th>{t("col_expiry")}</th>
                  <th>{t("col_check")}</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {results.map(({ draft: d, errors, warnings, pending, valid }) => (
                  <tr key={d.key} className={!pending && !valid ? "row-invalid" : ""}>
                    <td>
                      <strong className="cell-file">{d.file.name}</strong>
                      <span className="cell-sub">{formatFileSize(d.file.size)}</span>
                    </td>
                    <td><input className="cell-input" style={{ width: 84 }} value={d.code} onChange={e => changeCode(d, e.target.value)} placeholder="DOC-01" /></td>
                    <td><input className="cell-input" style={{ width: 190 }} value={d.titleEn} onChange={e => updateDraft(d.key, { titleEn: e.target.value })} /></td>
                    <td>
                      <select className="cell-input" value={d.category} onChange={e => updateDraft(d.key, { category: e.target.value })}>
                        <option value="">—</option>
                        {DOCUMENT_CATEGORIES.map(c => <option key={c} value={c}>{tv(c)}</option>)}
                      </select>
                    </td>
                    <td>
                      <select className="cell-input" value={d.department} onChange={e => updateDraft(d.key, { department: e.target.value })}>
                        <option value="">—</option>
                        {DEPARTMENTS.map(x => <option key={x} value={x}>{tv(x)}</option>)}
                      </select>
                    </td>
                    <td><input className="cell-input" style={{ width: 64 }} value={d.version} onChange={e => updateDraft(d.key, { version: e.target.value })} placeholder="1.0" /></td>
                    <td><input className="cell-input" type="date" lang={locale} value={d.effectiveDate} onChange={e => updateDraft(d.key, { effectiveDate: e.target.value })} /></td>
                    <td><input className="cell-input" type="date" lang={locale} value={d.expiryDate} onChange={e => updateDraft(d.key, { expiryDate: e.target.value })} /></td>
                    <td className="cell-check">
                      {pending ? (
                        <span className="check-pending"><Loader2 size={13} className="spin" /> {t("checking")}</span>
                      ) : (
                        <>
                          {errors.map((m, i) => <span key={`e${i}`} className="issue issue--error"><CircleAlert size={12} /> {t(m.key, m.vars)}</span>)}
                          {warnings.map((m, i) => <span key={`w${i}`} className="issue issue--warning"><CircleAlert size={12} /> {t(m.key, m.vars)}</span>)}
                          {valid && <span className="issue issue--ok"><CircleCheck size={12} /> {t("check_ok")}</span>}
                        </>
                      )}
                    </td>
                    <td>
                      <button className="icon-btn" title={t("remove_file")} aria-label={t("remove_file")} onClick={() => setDrafts(list => list.filter(x => x.key !== d.key))}><X size={15} /></button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}

      {saveError && <div className="notice notice--danger"><CircleAlert size={16} /><span>{saveError}</span></div>}

      <div className="modal-actions">
        <Button variant="secondary" onClick={requestClose} disabled={saving}>{t("cancel")}</Button>
        <Button onClick={save} disabled={saving || validDrafts.length === 0} icon={saving ? <Loader2 size={15} className="spin" /> : <Upload size={15} />}>
          {t("save_valid", { n: validDrafts.length })}
        </Button>
      </div>
    </Modal>
  );
}
