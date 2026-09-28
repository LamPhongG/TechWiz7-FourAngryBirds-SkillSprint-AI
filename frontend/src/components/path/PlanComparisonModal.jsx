import { useState, useMemo } from "react";
import {
  Layers3, Check, X, CircleAlert, Sparkles, FileText, ArrowRight,
  SlidersHorizontal, Award, BookOpen, Clock, Target
} from "../Icons";
import { Modal, Button, Badge, Card, StatCard } from "../UI";
import { useLanguage } from "../../contexts/LanguageContext";
import { usePaths } from "../../contexts/PathsContext";
import { ROLES as JOB_ROLES } from "../../data/company";
import { PathStatusBadge } from "./Badges";

/**
 * Training Plan Comparison Modal (Dual-Pipeline Comparison View).
 * Allows HR / Reviewers to visually compare 2 training plans or revisions side-by-side:
 * Duration, modules, tasks, assessment quizzes, source documents, and skill coverage.
 */
export default function PlanComparisonModal({ open, onClose, defaultPathAId, defaultPathBId }) {
  const { t, tv, pick, locale } = useLanguage();
  const { paths } = usePaths();

  const [pathAId, setPathAId] = useState(defaultPathAId || paths[0]?.id || "");
  const [pathBId, setPathBId] = useState(defaultPathBId || paths[1]?.id || paths[0]?.id || "");

  const pathA = useMemo(() => paths.find(p => p.id === pathAId) || paths[0], [paths, pathAId]);
  const pathB = useMemo(() => paths.find(p => p.id === pathBId) || paths[1] || paths[0], [paths, pathBId]);

  if (!open || !pathA || !pathB) return null;

  // Extract statistics for each path
  const statsA = {
    stagesCount: (pathA.stages || []).length,
    modulesCount: (pathA.stages || []).reduce((acc, s) => acc + (s.modules || []).length, 0),
    lessonsCount: (pathA.stages || []).reduce((acc, s) => acc + (s.modules || []).reduce((n, m) => n + (m.lessons || []).length, 0), 0),
    tasksCount: (pathA.stages || []).reduce((acc, s) => acc + (s.modules || []).reduce((n, m) => n + (m.tasks || []).length, 0), 0),
    quizzesCount: (pathA.stages || []).reduce((acc, s) => acc + (s.modules || []).reduce((n, m) => n + (m.quiz || []).length, 0), 0),
    sourcesCount: (pathA.sources || []).length,
    coverage: pathA.coverage?.score != null ? Math.round(pathA.coverage.score * 100) : null,
  };

  const statsB = {
    stagesCount: (pathB.stages || []).length,
    modulesCount: (pathB.stages || []).reduce((acc, s) => acc + (s.modules || []).length, 0),
    lessonsCount: (pathB.stages || []).reduce((acc, s) => acc + (s.modules || []).reduce((n, m) => n + (m.lessons || []).length, 0), 0),
    tasksCount: (pathB.stages || []).reduce((acc, s) => acc + (s.modules || []).reduce((n, m) => n + (m.tasks || []).length, 0), 0),
    quizzesCount: (pathB.stages || []).reduce((acc, s) => acc + (s.modules || []).reduce((n, m) => n + (m.quiz || []).length, 0), 0),
    sourcesCount: (pathB.sources || []).length,
    coverage: pathB.coverage?.score != null ? Math.round(pathB.coverage.score * 100) : null,
  };

  const roleA = JOB_ROLES.find(r => r.id === pathA.target?.role_id);
  const roleB = JOB_ROLES.find(r => r.id === pathB.target?.role_id);

  const diffLabel = (valA, valB, suffix = "") => {
    const diff = valA - valB;
    if (diff === 0) return <span style={{ color: "var(--muted)" }}>Equal</span>;
    if (diff > 0) return <span style={{ color: "#10b981", fontWeight: 700 }}>Plan A +{diff}{suffix}</span>;
    return <span style={{ color: "#6366f1", fontWeight: 700 }}>Plan B +{Math.abs(diff)}{suffix}</span>;
  };

  return (
    <Modal open={open} onClose={onClose} title="Dual-Pipeline Training Plan Comparison" size="xl">
      <div style={{ padding: "0 4px" }}>
        {/* 1. Header Selector */}
        <div style={{
          display: "grid",
          gridTemplateColumns: "1fr auto 1fr",
          gap: 16,
          alignItems: "center",
          marginBottom: 20,
          padding: 16,
          background: "var(--surface-elevated, #f8fafc)",
          borderRadius: "var(--radius-lg, 12px)",
          border: "1px solid var(--border)"
        }}>
          <div>
            <label style={{ display: "block", fontSize: 12, fontWeight: 700, textTransform: "uppercase", color: "var(--muted)", marginBottom: 6 }}>
              Plan A (Baseline / Reference)
            </label>
            <select
              className="input-select"
              value={pathAId}
              onChange={e => setPathAId(e.target.value)}
              style={{ width: "100%", fontWeight: 600 }}
            >
              {paths.map(p => (
                <option key={p.id} value={p.id}>{p.id} - {pick(p, "title")}</option>
              ))}
            </select>
          </div>

          <div style={{ textAlign: "center", padding: "0 8px" }}>
            <Badge tone="purple" large>VS</Badge>
          </div>

          <div>
            <label style={{ display: "block", fontSize: 12, fontWeight: 700, textTransform: "uppercase", color: "var(--muted)", marginBottom: 6 }}>
              Plan B (Comparison)
            </label>
            <select
              className="input-select"
              value={pathBId}
              onChange={e => setPathBId(e.target.value)}
              style={{ width: "100%", fontWeight: 600 }}
            >
              {paths.map(p => (
                <option key={p.id} value={p.id}>{p.id} - {pick(p, "title")}</option>
              ))}
            </select>
          </div>
        </div>

        {/* 2. Top Metric Cards */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))", gap: 12, marginBottom: 20 }}>
          <div className="card" style={{ padding: 12, textAlign: "center" }}>
            <div style={{ fontSize: 11, color: "var(--muted)", textTransform: "uppercase" }}>Total Modules</div>
            <div style={{ fontSize: 18, fontWeight: 800, marginTop: 4 }}>
              <span style={{ color: "#3b82f6" }}>{statsA.modulesCount}</span> vs <span style={{ color: "#8b5cf6" }}>{statsB.modulesCount}</span>
            </div>
            <div style={{ fontSize: 11, marginTop: 2 }}>{diffLabel(statsA.modulesCount, statsB.modulesCount)}</div>
          </div>

          <div className="card" style={{ padding: 12, textAlign: "center" }}>
            <div style={{ fontSize: 11, color: "var(--muted)", textTransform: "uppercase" }}>Practical Tasks</div>
            <div style={{ fontSize: 18, fontWeight: 800, marginTop: 4 }}>
              <span style={{ color: "#3b82f6" }}>{statsA.tasksCount}</span> vs <span style={{ color: "#8b5cf6" }}>{statsB.tasksCount}</span>
            </div>
            <div style={{ fontSize: 11, marginTop: 2 }}>{diffLabel(statsA.tasksCount, statsB.tasksCount)}</div>
          </div>

          <div className="card" style={{ padding: 12, textAlign: "center" }}>
            <div style={{ fontSize: 11, color: "var(--muted)", textTransform: "uppercase" }}>Quiz Questions</div>
            <div style={{ fontSize: 18, fontWeight: 800, marginTop: 4 }}>
              <span style={{ color: "#3b82f6" }}>{statsA.quizzesCount}</span> vs <span style={{ color: "#8b5cf6" }}>{statsB.quizzesCount}</span>
            </div>
            <div style={{ fontSize: 11, marginTop: 2 }}>{diffLabel(statsA.quizzesCount, statsB.quizzesCount)}</div>
          </div>

          <div className="card" style={{ padding: 12, textAlign: "center" }}>
            <div style={{ fontSize: 11, color: "var(--muted)", textTransform: "uppercase" }}>Referenced Docs</div>
            <div style={{ fontSize: 18, fontWeight: 800, marginTop: 4 }}>
              <span style={{ color: "#3b82f6" }}>{statsA.sourcesCount}</span> vs <span style={{ color: "#8b5cf6" }}>{statsB.sourcesCount}</span>
            </div>
            <div style={{ fontSize: 11, marginTop: 2 }}>{diffLabel(statsA.sourcesCount, statsB.sourcesCount)}</div>
          </div>

          <div className="card" style={{ padding: 12, textAlign: "center" }}>
            <div style={{ fontSize: 11, color: "var(--muted)", textTransform: "uppercase" }}>Coverage Score</div>
            <div style={{ fontSize: 18, fontWeight: 800, marginTop: 4 }}>
              <span style={{ color: "#3b82f6" }}>{statsA.coverage != null ? `${statsA.coverage}%` : "Not calculated"}</span> vs <span style={{ color: "#8b5cf6" }}>{statsB.coverage != null ? `${statsB.coverage}%` : "Not calculated"}</span>
            </div>
            <div style={{ fontSize: 11, marginTop: 2 }}>{statsA.coverage != null && statsB.coverage != null ? diffLabel(statsA.coverage, statsB.coverage, "%") : ""}</div>
          </div>
        </div>

        {/* 3. Detailed Side-by-Side Comparison Table */}
        <div style={{ overflowX: "auto", marginBottom: 20 }}>
          <table className="data-table" style={{ width: "100%", fontSize: 13 }}>
            <thead>
              <tr>
                <th style={{ width: "25%" }}>Comparison Criteria</th>
                <th style={{ width: "35%", background: "rgba(59, 130, 246, 0.05)" }}>Plan A: {pick(pathA, "title")}</th>
                <th style={{ width: "35%", background: "rgba(139, 92, 246, 0.05)" }}>Plan B: {pick(pathB, "title")}</th>
                <th style={{ width: "15%" }}>Evaluation</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td><strong>ID & Revision</strong></td>
                <td><code>{pathA.id}</code> (v{pathA.revision || 1})</td>
                <td><code>{pathB.id}</code> (v{pathB.revision || 1})</td>
                <td>{pathA.revision === pathB.revision ? "Same revision" : "Different revision"}</td>
              </tr>
              <tr>
                <td><strong>Role & Department</strong></td>
                <td>{pick(roleA, "name") || pathA.target?.role_id} · {pathA.target?.department}</td>
                <td>{pick(roleB, "name") || pathB.target?.role_id} · {pathB.target?.department}</td>
                <td>{pathA.target?.role_id === pathB.target?.role_id ? "Same target role" : "Different target role"}</td>
              </tr>
              <tr>
                <td><strong>Target Level</strong></td>
                <td><Badge tone="purple">{pathA.level || "Standard"}</Badge></td>
                <td><Badge tone="purple">{pathB.level || "Standard"}</Badge></td>
                <td>{pathA.level === pathB.level ? "Equivalent level" : "Different level"}</td>
              </tr>
              <tr>
                <td><strong>Approval Status</strong></td>
                <td><PathStatusBadge status={pathA.status} /></td>
                <td><PathStatusBadge status={pathB.status} /></td>
                <td>{pathA.status === pathB.status ? "Matching status" : "Different workflow status"}</td>
              </tr>
              <tr>
                <td><strong>AI Engine</strong></td>
                <td><code>{pathA.engine || "gemini-2.5-flash"}</code></td>
                <td><code>{pathB.engine || "gemini-2.5-flash"}</code></td>
                <td>{pathA.engine === pathB.engine ? "Identical AI model" : "Different AI model"}</td>
              </tr>
              <tr>
                <td><strong>Number of Stages</strong></td>
                <td><strong>{statsA.stagesCount}</strong> stages</td>
                <td><strong>{statsB.stagesCount}</strong> stages</td>
                <td>{diffLabel(statsA.stagesCount, statsB.stagesCount, " stages")}</td>
              </tr>
              <tr>
                <td><strong>Total Lessons</strong></td>
                <td><strong>{statsA.lessonsCount}</strong> lessons</td>
                <td><strong>{statsB.lessonsCount}</strong> lessons</td>
                <td>{diffLabel(statsA.lessonsCount, statsB.lessonsCount, " lessons")}</td>
              </tr>
              <tr>
                <td><strong>Practical Tasks</strong></td>
                <td><strong>{statsA.tasksCount}</strong> tasks</td>
                <td><strong>{statsB.tasksCount}</strong> tasks</td>
                <td>{diffLabel(statsA.tasksCount, statsB.tasksCount, " tasks")}</td>
              </tr>
              <tr>
                <td><strong>Quiz Questions</strong></td>
                <td><strong>{statsA.quizzesCount}</strong> questions</td>
                <td><strong>{statsB.quizzesCount}</strong> questions</td>
                <td>{diffLabel(statsA.quizzesCount, statsB.quizzesCount, " questions")}</td>
              </tr>
              <tr>
                <td><strong>Skill Coverage (Ground Truth)</strong></td>
                <td><strong style={{ color: "#10b981" }}>{statsA.coverage != null ? `${statsA.coverage}%` : "Not calculated"}</strong></td>
                <td><strong style={{ color: "#10b981" }}>{statsB.coverage != null ? `${statsB.coverage}%` : "Not calculated"}</strong></td>
                <td>{statsA.coverage != null && statsB.coverage != null ? diffLabel(statsA.coverage, statsB.coverage, "%") : "—"}</td>
              </tr>
            </tbody>
          </table>
        </div>

        {/* 4. Stage & Module Breakdown Comparison */}
        <h3 style={{ fontSize: 15, fontWeight: 700, margin: "16px 0 10px" }}>
          Stage Breakdown & Module Catalog
        </h3>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
          <div style={{ background: "#f8fafc", padding: 14, borderRadius: 8, border: "1px solid var(--border)" }}>
            <div style={{ fontWeight: 700, color: "#2563eb", marginBottom: 8, fontSize: 13 }}>
              Plan A Structure: {pick(pathA, "title")}
            </div>
            {(pathA.stages || []).map((s, idx) => (
              <div key={idx} style={{ marginBottom: 10 }}>
                <div style={{ fontSize: 12, fontWeight: 700, color: "var(--muted)", textTransform: "uppercase" }}>
                  {s.name || `Stage ${idx + 1}`} ({s.duration || "2 weeks"})
                </div>
                <ul style={{ margin: "4px 0 0 16px", padding: 0, fontSize: 12.5 }}>
                  {(s.modules || []).map((m, mIdx) => (
                    <li key={mIdx} style={{ margin: "3px 0" }}>
                      <strong>{pick(m, "title")}</strong>
                      <span className="cell-sub" style={{ marginLeft: 6 }}>
                        ({(m.lessons || []).length} lessons, {(m.tasks || []).length} tasks, {(m.quiz || []).length} questions)
                      </span>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>

          <div style={{ background: "#f8fafc", padding: 14, borderRadius: 8, border: "1px solid var(--border)" }}>
            <div style={{ fontWeight: 700, color: "#7c3aed", marginBottom: 8, fontSize: 13 }}>
              Plan B Structure: {pick(pathB, "title")}
            </div>
            {(pathB.stages || []).map((s, idx) => (
              <div key={idx} style={{ marginBottom: 10 }}>
                <div style={{ fontSize: 12, fontWeight: 700, color: "var(--muted)", textTransform: "uppercase" }}>
                  {s.name || `Stage ${idx + 1}`} ({s.duration || "2 weeks"})
                </div>
                <ul style={{ margin: "4px 0 0 16px", padding: 0, fontSize: 12.5 }}>
                  {(s.modules || []).map((m, mIdx) => (
                    <li key={mIdx} style={{ margin: "3px 0" }}>
                      <strong>{pick(m, "title")}</strong>
                      <span className="cell-sub" style={{ marginLeft: 6 }}>
                        ({(m.lessons || []).length} lessons, {(m.tasks || []).length} tasks, {(m.quiz || []).length} questions)
                      </span>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>

        <div style={{ display: "flex", justifyContent: "flex-end", marginTop: 20 }}>
          <Button variant="primary" onClick={onClose}>
            Close Comparison
          </Button>
        </div>
      </div>
    </Modal>
  );
}

