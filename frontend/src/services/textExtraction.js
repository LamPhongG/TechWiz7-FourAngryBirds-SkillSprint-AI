// Trích xuất văn bản trong trình duyệt khi chưa có backend.
// PDF: pdf.js (giữ số trang). DOCX: mammoth → HTML để giữ heading theo style Word.
// Thư viện được import động để không làm nặng bundle của các trang không dùng tới.

let pdfjsPromise = null;

async function loadPdfjs() {
  if (!pdfjsPromise) {
    pdfjsPromise = Promise.all([
      import("pdfjs-dist"),
      import("pdfjs-dist/build/pdf.worker.min.mjs?url"),
    ]).then(([pdfjs, worker]) => {
      pdfjs.GlobalWorkerOptions.workerSrc = worker.default;
      return pdfjs;
    });
    pdfjsPromise.catch(() => { pdfjsPromise = null; });
  }
  return pdfjsPromise;
}

// Ghép các text item của một trang thành dòng; pdf.js đánh dấu xuống dòng bằng hasEOL
function pageText(content) {
  let out = "";
  for (const item of content.items) {
    if (typeof item.str !== "string") continue;
    out += item.str;
    if (item.hasEOL) out += "\n";
    else if (item.str && !item.str.endsWith(" ")) out += " ";
  }
  return out.replace(/[ \t]+\n/g, "\n");
}

async function extractPdf(blob, onProgress) {
  const pdfjs = await loadPdfjs();
  const data = new Uint8Array(await blob.arrayBuffer());
  const pdf = await pdfjs.getDocument({ data }).promise;
  const blocks = [];
  try {
    for (let n = 1; n <= pdf.numPages; n++) {
      const page = await pdf.getPage(n);
      blocks.push({ page: n, text: pageText(await page.getTextContent()) });
      page.cleanup();
      onProgress?.(n / pdf.numPages);
    }
  } finally {
    pdf.destroy();
  }
  return { blocks, pageCount: pdf.numPages };
}

async function extractDocx(blob, onProgress) {
  const { default: mammoth } = await import("mammoth");
  onProgress?.(0.2);
  const { value: html } = await mammoth.convertToHtml({ arrayBuffer: await blob.arrayBuffer() });
  onProgress?.(0.8);
  const doc = new DOMParser().parseFromString(html, "text/html");
  const blocks = [];
  let current = { page: null, heading: "", text: "" };
  for (const el of doc.body.children) {
    const text = el.textContent.replace(/\s+/g, " ").trim();
    if (!text) continue;
    if (/^H[1-6]$/.test(el.tagName)) {
      if (current.text || current.heading) blocks.push(current);
      current = { page: null, heading: text, text: "" };
    } else if (el.tagName === "TABLE") {
      const rows = [...el.querySelectorAll("tr")].map(tr => [...tr.cells].map(c => c.textContent.trim()).join(" | "));
      current.text += `${rows.join("\n")}\n\n`;
    } else if (el.tagName === "UL" || el.tagName === "OL") {
      current.text += `${[...el.querySelectorAll("li")].map(li => `- ${li.textContent.trim()}`).join("\n")}\n\n`;
    } else {
      current.text += `${text}\n\n`;
    }
  }
  if (current.text || current.heading) blocks.push(current);
  onProgress?.(1);
  // DOCX không có khái niệm trang cố định — page để null, trích dẫn dùng heading/section
  return { blocks, pageCount: null };
}

/**
 * @returns {Promise<{blocks: Array<{page, text, heading?}>, pageCount: number|null, raw?: string}>}
 */
export async function extractText(blob, ext, onProgress) {
  if (ext === "pdf") return extractPdf(blob, onProgress);
  if (ext === "docx") return extractDocx(blob, onProgress);
  if (["txt", "md", "csv"].includes(ext)) {
    const text = await blob.text();
    onProgress?.(1);
    return { blocks: [{ page: null, text }], pageCount: null, raw: text };
  }
  throw new Error(`Unsupported format: .${ext}`);
}
