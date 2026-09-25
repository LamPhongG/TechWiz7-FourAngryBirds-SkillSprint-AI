import { describe, expect, it } from "vitest";
import { approvalRule, can, visibleToEmployee } from "../src/utils/pathWorkflow";
import { emptyEnrollment, moduleProgress, nextModule, pathProgress, scoreQuiz, stageUnlocked } from "../src/utils/progress";

describe("pathWorkflow — quyền theo vai trò", () => {
  const p = status => ({ status });

  it("HR edits and submits drafts and paths sent back; reviewer edits only while reviewing", () => {
    expect(can("hr", "edit", p("draft"))).toBe(true);
    expect(can("hr", "edit", p("changes_requested"))).toBe(true);
    expect(can("hr", "edit", p("in_review"))).toBe(false);
    expect(can("reviewer", "edit", p("in_review"))).toBe(true);
    expect(can("reviewer", "edit", p("draft"))).toBe(false);
    expect(can("hr", "submit", p("changes_requested"))).toBe(true);
  });

  it("only the reviewer approves or requests changes, and only while in review", () => {
    expect(can("reviewer", "approve", p("in_review"))).toBe(true);
    expect(can("hr", "approve", p("in_review"))).toBe(false);
    expect(can("reviewer", "request_changes", p("published"))).toBe(false);
    expect(can("employee", "approve", p("in_review"))).toBe(false);
  });

  it("published content is read-only", () => {
    expect(can("hr", "edit", p("published"))).toBe(false);
    expect(can("reviewer", "edit", p("published"))).toBe(false);
    expect(can("hr", "archive", p("published"))).toBe(true);
  });

  it("approval: blocked on blocking errors, reason required unless fully verified", () => {
    expect(approvalRule({ blocking: true, final_status: "manual_review" }).allowed).toBe(false);
    expect(approvalRule({ blocking: false, final_status: "verified" })).toEqual({ allowed: true, reasonRequired: false });
    expect(approvalRule({ blocking: false, final_status: "manual_review" })).toEqual({ allowed: true, reasonRequired: true });
  });

  it("employees see published paths for their department, company-wide, or their role", () => {
    const user = { department: "Engineering", role_id: "support-engineer" };
    const pub = to => ({ status: "published", published_to: to });
    expect(visibleToEmployee(pub({ departments: ["Engineering"], roles: [] }), user)).toBe(true);
    expect(visibleToEmployee(pub({ departments: ["Company-wide"], roles: [] }), user)).toBe(true);
    expect(visibleToEmployee(pub({ departments: [], roles: ["support-engineer"] }), user)).toBe(true);
    expect(visibleToEmployee(pub({ departments: ["Sales"], roles: ["sales-exec"] }), user)).toBe(false);
    expect(visibleToEmployee({ status: "in_review", published_to: { departments: ["Engineering"], roles: [] } }, user)).toBe(false);
  });
});

describe("progress — tiến độ học", () => {
  const quiz = [{ id: "q1", answer: 0 }, { id: "q2", answer: 1 }, { id: "q3", answer: 2 }];
  const path = {
    stages: [
      { key: "day1", modules: [{ id: "m1", lessons: [{ id: "l1" }], tasks: [{ id: "t1" }], quiz }] },
      { key: "week1", modules: [{ id: "m2", lessons: [{ id: "l2" }], tasks: [], quiz: [] }] },
    ],
  };

  it("scores quizzes with a 70% pass mark", () => {
    expect(scoreQuiz(quiz, { q1: 0, q2: 1, q3: 0 })).toEqual({ score: 2, total: 3, passed: false });
    expect(scoreQuiz(quiz, { q1: 0, q2: 1, q3: 2 }).passed).toBe(true);
  });

  it("completes a module only after lessons, tasks and a passed quiz", () => {
    const e = { ...emptyEnrollment(), lessonsRead: ["l1"], tasksDone: ["t1"] };
    expect(moduleProgress(path.stages[0].modules[0], e).complete).toBe(false);
    const passed = { ...e, quiz: { m1: [{ score: 3, total: 3 }] } };
    expect(moduleProgress(path.stages[0].modules[0], passed).complete).toBe(true);
  });

  it("locks the next stage until the previous one is complete", () => {
    const e = emptyEnrollment();
    expect(stageUnlocked(path, 0, e)).toBe(true);
    expect(stageUnlocked(path, 1, e)).toBe(false);
    expect(nextModule(path, e).module.id).toBe("m1");
    const done = { ...e, lessonsRead: ["l1"], tasksDone: ["t1"], quiz: { m1: [{ score: 3, total: 3 }] } };
    expect(stageUnlocked(path, 1, done)).toBe(true);
    expect(nextModule(path, done).module.id).toBe("m2");
    expect(pathProgress(path, done)).toMatchObject({ done: 1, total: 2, percent: 50, complete: false });
  });
});
