import { FileText, Quote, CircleCheck, CircleAlert } from "./Icons";
import { useLanguage } from "../contexts/LanguageContext";
import { useDocuments } from "../contexts/DocumentsContext";
import { findCatalogEntry } from "../utils/documentValidation";
import { findQuoteInChunks } from "../utils/chunker";

/**
 * Đối chiếu exact_quote với nội dung đã trích xuất của tài liệu trong kho.
 * @returns {{state: "found"|"not_found"|"not_processed"|"not_in_repo"|"no_quote", chunk?: object}}
 */
function useQuoteCheck(reference) {
  const { documents, chunksByDocId } = useDocuments();
  if (!reference?.exact_quote) return { state: "no_quote" };
  // Ưu tiên bản đang hiệu lực; không có thì dùng bản mới nhất của mã đó
  const candidates = documents.filter(d => d.code === reference.doc);
  const doc = candidates.find(d => d.status === "active") || candidates[0];
  if (!doc) return { state: "not_in_repo" };
  const chunks = chunksByDocId[doc.id];
  if (!chunks?.length) return { state: "not_processed", doc };
  const chunk = findQuoteInChunks(reference.exact_quote, chunks, reference.page);
  return chunk ? { state: "found", doc, chunk } : { state: "not_found", doc };
}

const CHECK_TONE = { found: "ok", not_found: "error", not_processed: "muted", not_in_repo: "muted", no_quote: "warning" };

function QuoteCheck({ reference }) {
  const { t } = useLanguage();
  const check = useQuoteCheck(reference);
  const tone = CHECK_TONE[check.state];
  const Icon = tone === "ok" ? CircleCheck : CircleAlert;
  // DOCX/TXT không có số trang — hiện heading của chunk thay cho trang
  const text = check.state !== "found"
    ? t(`quote_${check.state}`)
    : check.chunk.page != null
      ? t("quote_found", { chunk: check.chunk.chunk_id, page: check.chunk.page })
      : t("quote_found_section", { chunk: check.chunk.chunk_id, section: check.chunk.heading || check.chunk.section_id });
  return <span className={`quote-check quote-check--${tone}`}><Icon size={12} /> {text}</span>;
}

/**
 * Hiển thị source_reference theo Rules mục 4: tài liệu, mục, trang và câu trích nguyên văn.
 * @param {{doc: string, section?: string, page?: number|null, exact_quote?: string}} reference
 * @param {boolean} verify  có đối chiếu câu trích với kho tài liệu không
 */
export default function Citation({ reference, verify = true, compact = false }) {
  const { t, pick } = useLanguage();
  if (!reference) return null;
  const entry = findCatalogEntry(reference.doc);
  return (
    <div className={`citation ${compact ? "citation--compact" : ""}`}>
      <div className="citation__head">
        <FileText size={13} />
        <strong>{reference.doc}</strong>
        {entry && <span>{pick(entry, "title")}</span>}
        {reference.section && <span>· {reference.section}</span>}
        {reference.page != null && <span>· {t("page_abbr")}{reference.page}</span>}
      </div>
      {reference.exact_quote ? (
        <blockquote className="citation__quote"><Quote size={12} />{reference.exact_quote}</blockquote>
      ) : (
        <span className="quote-check quote-check--warning"><CircleAlert size={12} /> {t("quote_no_quote")}</span>
      )}
      {verify && reference.exact_quote && <QuoteCheck reference={reference} />}
    </div>
  );
}
