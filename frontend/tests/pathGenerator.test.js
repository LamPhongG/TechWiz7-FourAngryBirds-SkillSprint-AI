import { describe, expect, it } from "vitest";
import { generatePathContent, makeClozeQuestion, splitSentences, allModules } from "../src/utils/pathGenerator";
import { scanChunks } from "../src/utils/injectionScan";
import { normalizeForMatch } from "../src/utils/chunker";
import { docs, chunksByDocId, deployment } from "./fixtures";

const generate = (over = {}) => generatePathContent({ id: "LP-T", level: "Intermediate", purpose: "onboarding", docs, chunksByDocId, ...over });

describe("splitSentences / makeClozeQuestion", () => {
  it("splits paragraphs into sentences and drops fragments", () => {
    expect(splitSentences("First rule applies to all staff members. Second rule too.\n\nshort")).toEqual(["First rule applies to all staff members."]);
  });

  it("blanks the first standalone number and offers 3 different distractors", () => {
    const q = makeClozeQuestion("Every password must have at least 12 characters and be changed every 90 days.");
    expect(q.correct).toBe("12");
    expect(q.blanked).toContain("at least _____ characters");
    expect(new Set([q.correct, ...q.distractors]).size).toBe(4);
  });

  it("ignores numbers inside codes, versions and section numbering", () => {
    expect(makeClozeQuestion("See DOC-10 version v1.0 for the deployment workflow details.")).toBeNull();
    expect(makeClozeQuestion("1. Use a password manager for every company account you own.")).toBeNull();
  });
});

describe("generatePathContent", () => {
  const path = generate();
  const modules = allModules(path);

  it("orders stages by the onboarding template: handbook → company policy → department SOP → assessment", () => {
    expect(path.stages.map(s => s.key)).toEqual(["day1", "week1", "day30", "day90"]);
    expect(path.stages[0].modules[0].doc_code).toBe("DOC-01");
    expect(path.stages[1].modules[0].doc_code).toBe("DOC-06");
    expect(path.stages[2].modules[0].doc_code).toBe("DOC-10");
    expect(path.stages[3].modules[0].kind).toBe("assessment");
  });

  it("uses the promotion template when asked", () => {
    expect(generate({ purpose: "promotion" }).stages.map(s => s.key)).toEqual(["foundation", "deep", "assessment"]);
  });

  it("builds one lesson per document section with the original text", () => {
    const m = modules.find(x => x.doc_code === "DOC-06");
    expect(m.lessons.map(l => l.title)).toEqual(["Passwords", "Incident reporting"]);
    expect(m.lessons[1].content).toContain("#incident-response");
  });

  it("gives every lesson, task and question an exact quote that exists in the source", () => {
    for (const m of modules) {
      for (const item of [...m.lessons, ...m.tasks, ...m.quiz]) {
        const ref = item.source_reference;
        const source = chunksByDocId[ref.doc_id].map(c => normalizeForMatch(c.content)).join(" ");
        expect(source).toContain(normalizeForMatch(ref.exact_quote));
      }
    }
  });

  it("makes the correct quiz answer appear in its quote", () => {
    for (const q of modules.flatMap(m => m.quiz)) {
      expect(q.options).toHaveLength(4);
      expect(normalizeForMatch(q.source_reference.exact_quote)).toContain(normalizeForMatch(q.options[q.answer]));
    }
  });

  it("turns obligation sentences into work tasks", () => {
    const tasks = modules.flatMap(m => m.tasks.map(t => t.title));
    expect(tasks.some(t => /must/.test(t))).toBe(true);
  });

  it("scales quiz size with level", () => {
    const count = level => allModules(generate({ level })).filter(m => m.kind === "lesson").reduce((n, m) => n + m.quiz.length, 0);
    expect(count("Advanced")).toBeGreaterThanOrEqual(count("Beginner"));
  });

  it("excludes chunks flagged for prompt injection and records them", () => {
    const flags = scanChunks(deployment.chunks);
    const p = generate({ flagsByDocId: { d10: flags } });
    expect(p.excluded_chunks.length).toBeGreaterThan(0);
    const text = allModules(p).flatMap(m => m.lessons.map(l => l.content)).join(" ");
    expect(text).not.toMatch(/ignore previous instructions/i);
  });

  it("is deterministic for the same input", () => {
    expect(JSON.stringify(generate())).toBe(JSON.stringify(generate()));
  });

  it("fails clearly when nothing was extracted", () => {
    expect(() => generate({ chunksByDocId: {} })).toThrow("NO_CONTENT");
  });
});
