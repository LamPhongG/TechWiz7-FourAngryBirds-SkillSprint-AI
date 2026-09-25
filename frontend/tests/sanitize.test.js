import { describe, expect, it } from "vitest";
import { sanitizeAuditLog, sanitizeDocuments, sanitizeEnrollments, sanitizePaths } from "../src/services/sanitize";

const goodPath = {
  id: "LP-1", status: "published", target: { role_id: "support-engineer" },
  stages: [{ key: "day1", modules: [{ id: "M1", lessons: [], tasks: [], quiz: [{ id: "Q1", options: ["a", "b"] }] }] }],
  published_to: { departments: ["Engineering"], roles: [] },
};

describe("sanitize — dữ liệu cũ/hỏng trong trình duyệt không được làm trắng trang", () => {
  it("keeps valid paths and fills optional arrays", () => {
    const [p] = sanitizePaths([goodPath]);
    expect(p.id).toBe("LP-1");
    expect(p.comments).toEqual([]);
    expect(p.sources).toEqual([]);
  });

  it("drops malformed paths and non-array values", () => {
    expect(sanitizePaths({ a: 1 })).toEqual([]);
    expect(sanitizePaths("x")).toEqual([]);
    expect(sanitizePaths([null, { id: "LP-OLD", status: "published" }, { ...goodPath, published_to: null }, { ...goodPath, status: "weird" }])).toEqual([]);
    expect(sanitizePaths([{ ...goodPath, stages: [{ key: "day1", modules: [{ id: "M1" }] }] }])).toEqual([]);
  });

  it("keeps only well-formed audit entries", () => {
    expect(sanitizeAuditLog("x")).toEqual([]);
    expect(sanitizeAuditLog([{ id: "L1", action: "approve" }, { id: 2 }, null])).toEqual([{ id: "L1", action: "approve" }]);
  });

  it("repairs enrollments field by field", () => {
    const out = sanitizeEnrollments({ 1: { "LP-1": { quiz: null, lessonsRead: "x" }, bad: 3 }, 2: "x" });
    expect(out[1]["LP-1"]).toMatchObject({ lessonsRead: [], tasksDone: [], quiz: {} });
    expect(out[1].bad).toBeUndefined();
    expect(out[2]).toBeUndefined();
    expect(sanitizeEnrollments(null)).toEqual({});
  });

  it("drops document records without code, version or file name", () => {
    const doc = { id: "d1", code: "DOC-01", version: "1.0", fileName: "a.pdf" };
    expect(sanitizeDocuments([doc, { id: "d2" }, null])).toEqual([doc]);
  });
});
