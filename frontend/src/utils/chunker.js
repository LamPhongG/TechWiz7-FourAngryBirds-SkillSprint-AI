// Chia văn bản đã trích xuất thành chunk theo heading/section.
// Output khớp contract của backend (WBS Phase 1):
//   { doc_id, chunk_id, section_id, heading, page, content }
// Hàm thuần — không phụ thuộc trình duyệt để test được bằng Vitest.

export const MAX_CHUNK_CHARS = 1200;

// Heading phổ biến trong tài liệu chính sách: "1.", "2.3 Title", "Section 4", "Điều 5", "Chương II", markdown "#"
const HEADING_PATTERNS = [
  /^#{1,6}\s+\S/,
  /^(\d+(\.\d+){0,3})[.)]?\s+\S.{0,100}$/,
  /^(section|chapter|part|article|appendix)\s+[\dIVXLC]+\b/i,
  /^(điều|chương|mục|phần|phụ lục)\s+[\dIVXLC]+\b/i,
];

export function isHeadingLine(line) {
  const text = line.trim();
  if (!text || text.length > 120) return false;
  if (HEADING_PATTERNS.some(p => p.test(text))) return true;
  // Dòng ngắn viết hoa toàn bộ (tiêu đề in hoa trong PDF) — cần ít nhất 2 chữ cái để loại số trang, ký hiệu
  const letters = text.replace(/[^\p{L}]/gu, "");
  return letters.length >= 4 && text.length <= 80 && letters === letters.toUpperCase() && !/[.,;:]$/.test(text);
}

const cleanHeading = (line) => line.trim().replace(/^#{1,6}\s+/, "");

/**
 * Chia các khối văn bản thành chunk.
 * @param {string} docId
 * @param {Array<{page: number|null, text: string, heading?: string}>} blocks
 *   Mỗi khối là một trang (PDF) hoặc một đoạn đã biết heading (DOCX).
 * @returns {Array<{doc_id, chunk_id, section_id, heading, page, content}>}
 */
export function chunkBlocks(docId, blocks, { maxChars = MAX_CHUNK_CHARS } = {}) {
  const sections = [];
  let current = null;

  const startSection = (heading, page) => {
    current = { heading, page, parts: [] };
    sections.push(current);
  };

  for (const block of blocks) {
    if (block.heading) startSection(block.heading.trim(), block.page ?? null);
    const lines = String(block.text || "").split(/\r?\n/);
    for (const raw of lines) {
      const line = raw.replace(/\s+$/, "");
      if (!block.heading && isHeadingLine(line)) {
        startSection(cleanHeading(line), block.page ?? null);
        continue;
      }
      if (!line.trim()) {
        if (current?.parts.length) current.parts.push({ text: "", page: block.page ?? null });
        continue;
      }
      if (!current) startSection("", block.page ?? null);
      current.parts.push({ text: line.trim(), page: block.page ?? null });
    }
  }

  const chunks = [];
  sections.forEach((section, sIndex) => {
    const sectionId = `S${String(sIndex + 1).padStart(3, "0")}`;
    for (const piece of splitSection(section.parts, maxChars)) {
      chunks.push({
        doc_id: docId,
        chunk_id: `${docId}-C${String(chunks.length + 1).padStart(4, "0")}`,
        section_id: sectionId,
        heading: section.heading,
        page: piece.page ?? section.page,
        content: piece.content,
      });
    }
  });
  return chunks;
}

// Gom dòng thành đoạn (ngăn bởi dòng trống), rồi gom đoạn đến khi chạm maxChars.
// Một đoạn quá dài thì cắt theo câu để không chunk nào vượt giới hạn quá nhiều.
function splitSection(parts, maxChars) {
  const paragraphs = [];
  let para = null;
  for (const part of parts) {
    if (!part.text) { para = null; continue; }
    if (!para) { para = { page: part.page, text: part.text }; paragraphs.push(para); }
    else para.text += ` ${part.text}`;
  }

  const units = paragraphs.flatMap(p => (p.text.length <= maxChars ? [p] : splitLong(p, maxChars)));
  const pieces = [];
  let buf = null;
  for (const unit of units) {
    if (buf && buf.content.length + unit.text.length + 2 > maxChars) {
      pieces.push(buf);
      buf = null;
    }
    if (!buf) buf = { page: unit.page, content: unit.text };
    else buf.content += `\n\n${unit.text}`;
  }
  if (buf) pieces.push(buf);
  return pieces;
}

function splitLong(paragraph, maxChars) {
  const sentences = paragraph.text.match(/[^.!?。]+[.!?。]*\s*/g) || [paragraph.text];
  const out = [];
  let text = "";
  for (const s of sentences) {
    if (text && text.length + s.length > maxChars) { out.push({ page: paragraph.page, text: text.trim() }); text = ""; }
    // Câu đơn dài hơn giới hạn (bảng, danh sách không dấu chấm) — cắt cứng theo ký tự
    if (s.length > maxChars) {
      for (let i = 0; i < s.length; i += maxChars) out.push({ page: paragraph.page, text: s.slice(i, i + maxChars).trim() });
      continue;
    }
    text += s;
  }
  if (text.trim()) out.push({ page: paragraph.page, text: text.trim() });
  return out;
}

/**
 * CSV: mỗi chunk gồm dòng tiêu đề cột + tối đa `rowsPerChunk` dòng dữ liệu,
 * để chunk nào cũng tự đọc hiểu được mà không cần chunk trước.
 */
export function chunkCsv(docId, text, { rowsPerChunk = 25 } = {}) {
  const lines = String(text).split(/\r?\n/).filter(l => l.trim());
  if (lines.length === 0) return [];
  const [header, ...rows] = lines;
  if (rows.length === 0) return chunkBlocks(docId, [{ page: null, text: header }]);
  const chunks = [];
  for (let i = 0; i < rows.length; i += rowsPerChunk) {
    const n = chunks.length + 1;
    chunks.push({
      doc_id: docId,
      chunk_id: `${docId}-C${String(n).padStart(4, "0")}`,
      section_id: `S${String(n).padStart(3, "0")}`,
      heading: `Rows ${i + 1}–${Math.min(i + rowsPerChunk, rows.length)}`,
      page: null,
      content: [header, ...rows.slice(i, i + rowsPerChunk)].join("\n"),
    });
  }
  return chunks;
}

// Chuẩn hoá khoảng trắng + chữ thường để so khớp trích dẫn với nội dung chunk
export function normalizeForMatch(text) {
  return String(text || "")
    .normalize("NFC")
    .replace(/[‘’]/g, "'")
    .replace(/[“”]/g, '"')
    .replace(/[–—]/g, "-")
    .replace(/\s+/g, " ")
    .trim()
    .toLowerCase();
}

/**
 * Tìm chunk chứa nguyên văn câu trích dẫn (exact_quote).
 * @returns {object|null} chunk đầu tiên khớp, ưu tiên chunk cùng trang nếu biết trang
 */
export function findQuoteInChunks(quote, chunks, page = null) {
  const needle = normalizeForMatch(quote);
  if (!needle || !chunks?.length) return null;
  const hits = chunks.filter(c => normalizeForMatch(c.content).includes(needle));
  if (hits.length === 0) return null;
  return hits.find(c => page != null && c.page === page) || hits[0];
}
