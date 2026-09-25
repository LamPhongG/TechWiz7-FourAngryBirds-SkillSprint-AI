import { describe, expect, it } from "vitest";
import { chunkBlocks, chunkCsv, findQuoteInChunks, isHeadingLine, MAX_CHUNK_CHARS } from "../src/utils/chunker";

describe("isHeadingLine", () => {
  it.each([
    "1. Purpose",
    "2.3 Leave entitlement",
    "## Security incidents",
    "Section 4",
    "Điều 5",
    "Chương II",
    "INFORMATION SECURITY POLICY",
  ])("treats %s as a heading", line => expect(isHeadingLine(line)).toBe(true));

  it.each([
    "",
    "Employees must report incidents within 24 hours.",
    "12",
    "A.",
    "This line is intentionally long enough that it cannot be a heading because headings are short and this sentence keeps going on.",
  ])("does not treat %j as a heading", line => expect(isHeadingLine(line)).toBe(false));
});

describe("chunkBlocks", () => {
  const pages = [
    { page: 1, text: "EMPLOYEE HANDBOOK\n1. Purpose\nThis handbook explains company rules.\n\n2. Working hours\nOffice hours are 8:30 to 17:30." },
    { page: 2, text: "3. Leave\nEmployees receive 12 days of annual leave." },
  ];

  it("produces chunks with the backend contract fields", () => {
    const chunks = chunkBlocks("DOC-01", pages);
    for (const c of chunks) {
      expect(Object.keys(c).sort()).toEqual(["chunk_id", "content", "doc_id", "heading", "page", "section_id"]);
      expect(c.doc_id).toBe("DOC-01");
    }
  });

  it("splits on headings and keeps the page number", () => {
    const chunks = chunkBlocks("DOC-01", pages);
    const leave = chunks.find(c => c.heading === "3. Leave");
    expect(leave.page).toBe(2);
    expect(leave.content).toContain("12 days of annual leave");
    expect(chunks.find(c => c.heading === "2. Working hours").content).toContain("8:30 to 17:30");
  });

  it("gives unique, ordered chunk ids", () => {
    const ids = chunkBlocks("DOC-01", pages).map(c => c.chunk_id);
    expect(new Set(ids).size).toBe(ids.length);
    expect(ids[0]).toBe("DOC-01-C0001");
  });

  it("uses the known heading of DOCX blocks without re-detecting headings", () => {
    const chunks = chunkBlocks("DOC-06", [{ page: null, heading: "Passwords", text: "1. Use at least 12 characters.\n\n" }]);
    expect(chunks).toHaveLength(1);
    expect(chunks[0].heading).toBe("Passwords");
    expect(chunks[0].content).toContain("1. Use at least 12 characters.");
  });

  it("keeps every chunk close to the size limit", () => {
    const long = Array.from({ length: 200 }, (_, i) => `Sentence number ${i} explains a rule.`).join(" ");
    const chunks = chunkBlocks("DOC-05", [{ page: 1, text: long }]);
    expect(chunks.length).toBeGreaterThan(1);
    for (const c of chunks) expect(c.content.length).toBeLessThanOrEqual(MAX_CHUNK_CHARS);
    expect(chunks.map(c => c.content).join(" ").replace(/\s+/g, " ")).toBe(long);
  });

  it("returns nothing for empty text", () => {
    expect(chunkBlocks("DOC-01", [{ page: 1, text: "   \n\n" }])).toEqual([]);
  });
});

describe("chunkCsv", () => {
  it("repeats the header row in every chunk", () => {
    const rows = Array.from({ length: 30 }, (_, i) => `r${i},value${i}`);
    const chunks = chunkCsv("DOC-99", ["id,value", ...rows].join("\n"), { rowsPerChunk: 10 });
    expect(chunks).toHaveLength(3);
    for (const c of chunks) expect(c.content.startsWith("id,value\n")).toBe(true);
  });
});

describe("findQuoteInChunks", () => {
  const chunks = [
    { chunk_id: "A", page: 3, content: "Security incidents must be reported immediately\nin the #incident-response Slack channel." },
    { chunk_id: "B", page: 12, content: "Security incidents must be reported immediately in the #incident-response Slack channel." },
  ];

  it("matches ignoring case, line breaks and curly quotes", () => {
    expect(findQuoteInChunks("security INCIDENTS must be reported immediately in the #incident-response Slack channel.", chunks)?.chunk_id).toBe("A");
    expect(findQuoteInChunks("Don’t share passwords", [{ chunk_id: "C", page: 1, content: "Don't share passwords." }])?.chunk_id).toBe("C");
  });

  it("prefers the chunk on the cited page", () => {
    expect(findQuoteInChunks("Security incidents must be reported immediately", chunks, 12).chunk_id).toBe("B");
  });

  it("returns null when the quote is not in the document", () => {
    expect(findQuoteInChunks("Report suspected incidents in the #security-alerts channel.", chunks)).toBeNull();
    expect(findQuoteInChunks("", chunks)).toBeNull();
  });
});
