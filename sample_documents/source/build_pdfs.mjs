// Render every DOC-*.md in this folder to ../DOC-XX_<family>_v<version>.pdf with headless Chrome.
// A later version of a document is its own source file, named DOC-XX_<family>_v<version>.md.
//
//   cd sample_documents/source
//   npm install
//   node build_pdfs.mjs                        # all documents
//   node build_pdfs.mjs DOC-12 DOC-18          # every version of these
//   node build_pdfs.mjs DOC-12_v2.0            # one version only
//
// Chrome path: CHROME_PATH, else the default Windows install location.
// No running header/footer on purpose: its text would be extracted into every page's chunks.
import { readFileSync, readdirSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { marked } from "marked";
import puppeteer from "puppeteer-core";

const here = path.dirname(fileURLToPath(import.meta.url));
const outDir = path.resolve(here, "..");
const only = new Set(process.argv.slice(2));
const chrome = process.env.CHROME_PATH || "C:/Program Files/Google/Chrome/Application/chrome.exe";

const FIELDS = [
  ["document_id", "Document ID"], ["title_vi", "Vietnamese title"], ["category", "Category"],
  ["department", "Department"], ["version", "Version"], ["status", "Status"],
  ["effective_date", "Effective date"], ["expiry_date", "Expiry date"], ["owner", "Owner"],
  ["supersedes", "Supersedes"], ["superseded_by", "Superseded by"],
];

const CSS = `
  @page { size: A4; margin: 22mm 20mm 22mm 20mm; }
  body { font-family: "Segoe UI", Arial, sans-serif; font-size: 10.5pt; line-height: 1.5; color: #1f2937; }
  .company { font-size: 9pt; letter-spacing: .04em; color: #6d28d9; margin: 0 0 4px; }  /* no text-transform: uppercase text would be read as a heading */
  h1 { font-size: 20pt; margin: 0 0 12px; color: #111827; }
  h2 { font-size: 13pt; margin: 18px 0 6px; color: #312e81; border-bottom: 1px solid #e5e7eb; padding-bottom: 3px; break-after: avoid; }
  h3 { font-size: 11pt; margin: 12px 0 4px; color: #1e3a8a; break-after: avoid; }
  p { margin: 0 0 8px; text-align: justify; }
  ul, ol { margin: 0 0 8px; padding-left: 20px; } li { margin: 0 0 3px; }
  table { border-collapse: collapse; width: 100%; margin: 6px 0 10px; font-size: 9.5pt; break-inside: auto; }
  th, td { border: 1px solid #d1d5db; padding: 4px 6px; text-align: left; vertical-align: top; }
  th { background: #f3f4f6; }
  table.meta { font-size: 9pt; margin-bottom: 16px; } table.meta th { width: 28%; }
  blockquote { margin: 8px 0; padding: 6px 12px; border-left: 3px solid #f59e0b; background: #fffbeb; }
`;

function parse(md) {
  const m = md.match(/^---\r?\n([\s\S]*?)\r?\n---\r?\n/);
  const meta = {};
  if (m) for (const line of m[1].split(/\r?\n/)) {
    const i = line.indexOf(":");
    if (i > 0) meta[line.slice(0, i).trim()] = line.slice(i + 1).trim();
  }
  return { meta, body: m ? md.slice(m[0].length) : md };
}

const esc = s => String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;");

function html({ meta, body }) {
  const rows = FIELDS.filter(([k]) => meta[k]).map(([k, label]) => `<tr><th>${label}</th><td>${esc(meta[k])}</td></tr>`).join("");
  return `<!doctype html><html><head><meta charset="utf-8"><style>${CSS}</style></head><body>
    <p class="company">FourAngryBirds EdTech &amp; HR Solutions JSC</p>
    ${marked.parse(body.replace(/^#\s+(.+)$/m, "# $1\n\n@@META@@")).replace("<p>@@META@@</p>", `<table class="meta">${rows}</table>`)}
  </body></html>`;
}

const docs = readdirSync(here)
  .filter(f => /^DOC-\d+_.+\.md$/.test(f))
  .map(file => {
    const doc = parse(readFileSync(path.join(here, file), "utf8"));
    const version = doc.meta.version || "1.0";
    const code = file.slice(0, 6);
    return { file, doc, version, code, name: `${file.replace(/(_v[\d.]+)?\.md$/, "")}_v${version}` };
  })
  // Sources with `format: docx | md | txt` are built by build_other_formats.py.
  .filter(d => (d.doc.meta.format || "pdf") === "pdf")
  .filter(d => !only.size || only.has(d.code) || only.has(`${d.code}_v${d.version}`));
const browser = await puppeteer.launch({ executablePath: chrome, headless: true });
try {
  const page = await browser.newPage();
  for (const { doc, name } of docs) {
    const out = path.join(outDir, `${name}.pdf`);
    await page.setContent(html(doc), { waitUntil: "load" });
    await page.pdf({ path: out, format: "A4", printBackground: true, preferCSSPageSize: true });
    console.log("wrote", path.relative(outDir, out));
  }
} finally {
  await browser.close();
}
