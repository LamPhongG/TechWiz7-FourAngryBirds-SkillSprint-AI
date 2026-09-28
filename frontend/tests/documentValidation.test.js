import { describe, expect, it } from "vitest";
import { buildDraft, getExtension, validateDraft } from "../src/utils/documentValidation";

const fileNamed = name => new File(["# Leave\nRequest 5 days ahead."], name, { lastModified: 0 });

describe("documentValidation — đuôi file", () => {
  it("maps .markdown to md and keeps other extensions", () => {
    expect(getExtension("DOC-03_hr-leave-policy_v1.1.markdown")).toBe("md");
    expect(getExtension("Policy.MARKDOWN")).toBe("md");
    expect(getExtension("a.pdf")).toBe("pdf");
    expect(getExtension("no-extension")).toBe("");
  });

  it("accepts a .markdown upload and still parses code and version from the name", () => {
    const draft = buildDraft(fileNamed("DOC-03_hr-leave-policy_v1.1.markdown"), { today: "2026-09-26" });

    expect([draft.ext, draft.code, draft.version]).toEqual(["md", "DOC-03", "1.1"]);
    const { errors } = validateDraft(draft, { existing: [], batch: [draft], today: "2026-09-26" });
    expect(errors.filter(e => e.key === "err_file_type")).toEqual([]);
  });

  it("lists .markdown among allowed types when rejecting a file", () => {
    const draft = buildDraft(fileNamed("tool.exe"), { today: "2026-09-26" });

    const { errors } = validateDraft(draft, { existing: [], batch: [draft], today: "2026-09-26" });
    expect(errors.find(e => e.key === "err_file_type").vars.list).toContain(".markdown");
  });
});
