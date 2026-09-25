import { useMemo, useState } from "react";
import { Layers3, RefreshCw, ShieldAlert, CircleAlert, ScanText } from "./Icons";
import { Badge, Modal, ProgressBar, SearchInput } from "./UI";
import InjectionFlagList from "./InjectionFlagList";
import { useLanguage } from "../contexts/LanguageContext";
import { useDocuments } from "../contexts/DocumentsContext";
import { flaggedChunkIds } from "../utils/injectionScan";

// Lỗi do documentProcessing ném ra bằng mã; lỗi khác hiện nguyên văn
const ERROR_KEYS = { NO_TEXT_LAYER: "proc_err_no_text_layer", NO_TEXT: "proc_err_no_text" };

/**
 * Cột "Xử lý" của bảng tài liệu: tiến độ 0–100% khi đang chạy, số chunk và cờ injection khi xong.
 */
export function ProcessingCell({ doc, onOpenChunks }) {
  const { t } = useLanguage();
  const { progress, processDocuments } = useDocuments();
  const running = progress[doc.id];

  if (running) {
    return (
      <div className="proc-cell">
        <ProgressBar value={running.percent} showValue />
        <span className="cell-sub">{t(`proc_stage_${running.stage}`)}</span>
      </div>
    );
  }
  if (doc.processing === "done") {
    return (
      <div className="proc-cell">
        <button className="link-btn" onClick={() => onOpenChunks(doc)}>
          <Layers3 size={13} /> {t("chunks_count", { n: doc.chunkCount ?? 0 })}
        </button>
        {doc.injectionFlagCount > 0 ? (
          <Badge tone="red"><ShieldAlert size={12} /> {t("injection_count", { n: doc.injectionFlagCount })}</Badge>
        ) : (
          <span className="cell-sub">{t(doc.processingEngine === "backend" ? "engine_backend" : "engine_browser")}</span>
        )}
      </div>
    );
  }
  if (doc.processing === "failed") {
    return (
      <div className="proc-cell">
        <Badge tone="red"><CircleAlert size={12} /> {t("proc_failed")}</Badge>
        <span className="cell-sub" title={doc.processingError}>{t(ERROR_KEYS[doc.processingError] || "proc_err_generic", { msg: doc.processingError })}</span>
        <button className="link-btn" onClick={() => processDocuments([doc])}><RefreshCw size={12} /> {t("proc_retry")}</button>
      </div>
    );
  }
  return (
    <div className="proc-cell">
      <Badge tone="orange">{t("processing_pending")}</Badge>
      <button className="link-btn" onClick={() => processDocuments([doc])}><ScanText size={12} /> {t("proc_run")}</button>
    </div>
  );
}

/** Danh sách chunk sau khi trích xuất; chunk bị gắn cờ injection được tô đỏ và đánh dấu đoạn khớp */
export function ChunksModal({ doc, onClose }) {
  const { t, pick } = useLanguage();
  const { processed } = useDocuments();
  const [query, setQuery] = useState("");
  const [onlyFlagged, setOnlyFlagged] = useState(false);
  const result = doc ? processed[doc.id] : null;
  const flags = useMemo(() => result?.injection_flags || [], [result]);
  const flagged = useMemo(() => flaggedChunkIds(flags), [flags]);

  if (!doc) return null;
  const q = query.trim().toLowerCase();
  const chunks = (result?.chunks || [])
    .filter(c => !onlyFlagged || flagged.has(c.chunk_id))
    .filter(c => !q || c.content.toLowerCase().includes(q) || c.heading?.toLowerCase().includes(q));

  return (
    <Modal open title={t("chunks_title", { code: doc.code, title: pick(doc, "title"), version: doc.version })} onClose={onClose} width="980px">
      {!result ? (
        <p className="cell-sub">{t("chunks_not_loaded")}</p>
      ) : (
        <>
          <div className="chunk-meta">
            <span>{t("chunks_count", { n: result.chunks.length })}</span>
            {result.page_count != null && <span>{t("pages_count", { n: result.page_count })}</span>}
            <span>{t("chars_count", { n: result.char_count.toLocaleString() })}</span>
            <span>{t(result.engine === "backend" ? "engine_backend" : "engine_browser")}</span>
          </div>

          {flags.length > 0 && (
            <div className="notice notice--danger" style={{ display: "block" }}>
              <strong><ShieldAlert size={15} /> {t("injection_doc_warning", { n: flags.length })}</strong>
              <InjectionFlagList flags={flags} />
            </div>
          )}

          <div className="toolbar" style={{ justifyContent: "space-between", flexWrap: "wrap" }}>
            <SearchInput value={query} onChange={setQuery} placeholder={t("search_chunks")} />
            {flags.length > 0 && (
              <div className="filter-tabs">
                <button className={!onlyFlagged ? "active" : ""} onClick={() => setOnlyFlagged(false)}>{t("filter_all")}</button>
                <button className={onlyFlagged ? "active" : ""} onClick={() => setOnlyFlagged(true)}>{t("chunks_only_flagged")} ({flagged.size})</button>
              </div>
            )}
          </div>

          <div className="chunk-list">
            {chunks.map(c => (
              <article key={c.chunk_id} className={`chunk ${flagged.has(c.chunk_id) ? "chunk--flagged" : ""}`}>
                <header>
                  <strong>{c.chunk_id}</strong>
                  <span>{c.section_id}</span>
                  {c.page != null && <span>{t("page_abbr")}{c.page}</span>}
                  {c.heading && <em>{c.heading}</em>}
                  {flagged.has(c.chunk_id) && <Badge tone="red"><ShieldAlert size={11} /> {t("flag_injection")}</Badge>}
                </header>
                <p>{highlight(c.content, flags.filter(f => f.chunk_id === c.chunk_id).map(f => f.match))}</p>
              </article>
            ))}
            {chunks.length === 0 && <p className="cell-sub" style={{ textAlign: "center", padding: 16 }}>{t("repo_no_match")}</p>}
          </div>
        </>
      )}
    </Modal>
  );
}

function highlight(text, matches) {
  if (!matches.length) return text;
  const escaped = matches.map(m => m.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"));
  const parts = text.split(new RegExp(`(${escaped.join("|")})`, "gi"));
  return parts.map((part, i) => (i % 2 === 1 ? <mark key={i}>{part}</mark> : part));
}
