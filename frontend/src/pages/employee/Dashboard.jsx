import { useState, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { RouteIcon, BookOpen, CheckSquare, ClipboardCheck, ArrowUpRight, Play, CircleCheck, CircleAlert, Compass, Award, BrainCircuit, LockKeyhole } from "../../components/Icons";
import { Card, SectionHeader, StatCard, Button, ProgressBar, Badge, EmptyState, Toast } from "../../components/UI";
import ChangePasswordModal from "../../components/ChangePasswordModal";
import { useLanguage } from "../../contexts/LanguageContext";
import { useEnrollment } from "../../contexts/EnrollmentContext";
import { useAuth } from "../../hooks/useAuth";
import { useMyPaths } from "../../hooks/useMyPaths";
import { usePaths } from "../../contexts/PathsContext";
import { bestAttempt, moduleProgress, nextModule, pathProgress } from "../../utils/progress";
import { backendEnabled } from "../../services/apiClient";
import { formatLocalDate } from "../../utils/helpers";
import CertificateModal from "../../components/path/CertificateModal";

// "Later" preference stored per user in browser; banner dismisses automatically when password changed
const reminderKey = id => `skillsprint.pwdReminderDismissed.${id}`;
function reminderDismissed(id) {
  try { return localStorage.getItem(reminderKey(id)) === "1"; } catch { return false; }
}

/** Prompt employee to change temporary password sent by Admin via email; employee may change now or postpone */
function TemporaryPasswordBanner({ user }) {
  const { t } = useLanguage();
  const [dismissed, setDismissed] = useState(() => reminderDismissed(user.id));
  const [open, setOpen] = useState(false);
  const [toast, setToast] = useState(null);
  const later = () => {
    try { localStorage.setItem(reminderKey(user.id), "1"); } catch { /* storage blocked: dismiss for this session only */ }
    setDismissed(true);
  };
  return (
    <>
      {user.passwordIsTemporary && !dismissed && (
        <div className="notice notice--warning" data-testid="temp-password-banner" style={{ alignItems: "center", marginBottom: "1.25rem" }}>
          <LockKeyhole size={18} />
          <div style={{ flex: 1 }}>
            <strong>{t("pwd_banner_title")}</strong>
            <div style={{ fontSize: 14, marginTop: 2 }}>{t("pwd_banner_desc")}</div>
          </div>
          <Button variant="ghost" onClick={later}>{t("pwd_banner_later")}</Button>
          <Button onClick={() => setOpen(true)}>{t("pwd_change")}</Button>
        </div>
      )}
      <ChangePasswordModal open={open} onClose={() => setOpen(false)} onDone={setToast} />
      <Toast message={toast} onClose={() => setToast(null)} />
    </>
  );
}

export default function EmployeeDashboard() {
  const navigate = useNavigate();
  const { t, tv, pick, locale } = useLanguage();
  const { user } = useAuth();
  const { enrollmentFor } = useEnrollment();
  const myPaths = useMyPaths();
  const { loaded } = usePaths();
  const [certPath, setCertPath] = useState(null);

  let modulesDone = 0, modulesTotal = 0, tasksDone = 0, tasksTotal = 0;
  const scores = [];
  for (const p of myPaths) {
    const e = enrollmentFor(p.id);
    for (const s of p.stages) {
      for (const m of s.modules) {
        const mp = moduleProgress(m, e);
        modulesTotal++;
        if (mp.complete) modulesDone++;
        tasksDone += mp.tasksDone;
        tasksTotal += m.tasks.length;
        const best = bestAttempt(e, m.id);
        if (best) scores.push(best.score / best.total);
      }
    }
  }
  const avg = scores.length ? Math.round((scores.reduce((a, b) => a + b, 0) / scores.length) * 100) : null;

  // Incomplete paths first, then by closest due date; paths without due date (optional/self-enrolled) last
  const learning = myPaths.map(p => ({ p, e: enrollmentFor(p.id) })).map(x => ({ ...x, prog: pathProgress(x.p, x.e) }))
    .sort((a, b) => (a.prog.complete - b.prog.complete) || (a.e.dueDate || "9999").localeCompare(b.e.dueDate || "9999"));
  const date = iso => formatLocalDate(iso, locale, { day: "2-digit", month: "2-digit", year: "numeric" });
  const exploreButton = backendEnabled() && (
    <Button variant="secondary" icon={<Compass size={15} />} onClick={() => navigate("/employee/explore")}>{t("explore_more")}</Button>
  );

  // Weak-area detection and adaptive recommendations
  const weakModules = useMemo(() => {
    const list = [];
    for (const p of myPaths) {
      const e = enrollmentFor(p.id);
      if (!e) continue;
      for (const s of p.stages || []) {
        for (const m of s.modules || []) {
          if (!m.quiz || m.quiz.length === 0) continue;
          const best = bestAttempt(e, m.id);
          if (best) {
            const ratio = best.total > 0 ? (best.score / best.total) : 0;
            if (ratio < 0.70) {
              list.push({
                pathId: p.id,
                pathTitle: pick(p, "title"),
                stageName: s.name,
                moduleId: m.id,
                moduleTitle: pick(m, "title"),
                score: best.score,
                total: best.total,
                percent: Math.round(ratio * 100),
              });
            }
          }
        }
      }
    }
    return list;
  }, [myPaths, enrollmentFor, pick]);

  return (
    <div>
      <div className="page-heading">
        <div>
          <span className="eyebrow">{t("role_employee")} · {tv(user.department)}</span>
          <h1>{t("dashboard_greeting", { name: user.name.split(" ")[0] })}</h1>
          <p>{t("employee_dashboard_desc", { role: user.role })}</p>
        </div>
        <div className="heading-actions">{exploreButton}</div>
      </div>

      <TemporaryPasswordBanner user={user} />

      <div className="stat-grid">
        <StatCard label={t("my_paths_count")} value={myPaths.length} icon={RouteIcon} tone="purple" />
        <StatCard label={t("modules_done")} value={`${modulesDone} / ${modulesTotal}`} icon={BookOpen} tone="blue" />
        <StatCard label={t("tasks_completed")} value={`${tasksDone} / ${tasksTotal}`} icon={CheckSquare} tone="green" />
        <StatCard label={t("quiz_average")} value={avg == null ? "—" : `${avg}%`} icon={ClipboardCheck} tone="orange" />
      </div>

      {!loaded ? (
        <Card><p className="cell-sub">{t("explore_loading")}</p></Card>
      ) : myPaths.length === 0 ? (
        <Card><EmptyState title={t("no_assigned_paths")} description={t("no_assigned_paths_desc", { department: tv(user.department) })} action={exploreButton} /></Card>
      ) : (
        <>
          {learning.some(x => x.prog.complete) && (
            <div className="card celebration-banner" style={{
              background: "linear-gradient(135deg, rgba(234, 179, 8, 0.12) 0%, rgba(99, 102, 241, 0.12) 100%)",
              border: "1px solid rgba(234, 179, 8, 0.35)",
              borderRadius: "var(--radius-lg, 12px)",
              marginBottom: "1.25rem",
              padding: "1.25rem 1.5rem",
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              flexWrap: "wrap",
              gap: "1rem"
            }}>
              <div style={{ display: "flex", alignItems: "center", gap: "1rem" }}>
                <div style={{
                  width: 44,
                  height: 44,
                  borderRadius: "50%",
                  background: "#fef08a",
                  color: "#854d0e",
                  display: "grid",
                  placeItems: "center",
                  boxShadow: "0 2px 8px rgba(202, 138, 4, 0.25)",
                  flexShrink: 0
                }}>
                  <Award size={24} />
                </div>
                <div>
                  <h3 style={{ margin: 0, fontSize: "1.05rem", fontWeight: 700 }}>
                    {t("congrats_completed_title")}
                  </h3>
                  <p style={{ margin: "3px 0 0", fontSize: "0.875rem", color: "var(--text-muted)" }}>
                    {t("congrats_completed_desc")}
                  </p>
                </div>
              </div>
              <Button variant="primary" icon={<Award size={15} />} onClick={() => setCertPath(learning.find(x => x.prog.complete))}>
                {t("view_certificate")}
              </Button>
            </div>
          )}

          {weakModules.length > 0 && (
            <div className="card" style={{
              background: "linear-gradient(135deg, rgba(239, 68, 68, 0.05) 0%, rgba(245, 158, 11, 0.07) 100%)",
              border: "1px solid rgba(245, 158, 11, 0.35)",
              borderRadius: "var(--radius-lg, 12px)",
              marginBottom: "1.25rem",
              padding: "1.25rem 1.5rem",
            }}>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 12, marginBottom: 12 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                  <div style={{
                    width: 38,
                    height: 38,
                    borderRadius: "50%",
                    background: "#fef3c7",
                    color: "#d97706",
                    display: "grid",
                    placeItems: "center",
                    flexShrink: 0
                  }}>
                    <BrainCircuit size={20} />
                  </div>
                  <div>
                    <h3 style={{ margin: 0, fontSize: "1rem", fontWeight: 700, color: "#92400e" }}>
                      Adaptive Learning Recommendations & Weak-Area Reinforcement
                    </h3>
                    <p style={{ margin: "2px 0 0", fontSize: "0.85rem", color: "var(--muted)" }}>
                      AI detected {weakModules.length} module{weakModules.length > 1 ? "s" : ""} with quiz scores &lt; 70%. Review the materials to reinforce your knowledge:
                    </p>
                  </div>
                </div>
                <Badge tone="orange">{weakModules.length} module{weakModules.length > 1 ? "s" : ""} to reinforce</Badge>
              </div>

              <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                {weakModules.map(wm => (
                  <div key={`${wm.pathId}-${wm.moduleId}`} style={{
                    background: "var(--surface, #ffffff)",
                    border: "1px solid var(--border)",
                    borderRadius: "var(--radius-md, 8px)",
                    padding: "10px 14px",
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    flexWrap: "wrap",
                    gap: 10
                  }}>
                    <div>
                      <div style={{ fontWeight: 600, fontSize: 13.5 }}>{wm.moduleTitle}</div>
                      <div className="cell-sub" style={{ fontSize: 12 }}>
                        {wm.pathTitle} · {wm.stageName} · Current Score: <strong style={{ color: "#ef4444" }}>{wm.score}/{wm.total} ({wm.percent}%)</strong>
                      </div>
                    </div>
                    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                      <span className="doc-chip" style={{ fontSize: 11, background: "rgba(245, 158, 11, 0.15)", color: "#b45309" }}>
                        Review theory & retake quiz
                      </span>
                      <Button
                        size="sm"
                        variant="primary"
                        icon={<Play size={13} />}
                        onClick={() => navigate(`/employee/paths/${wm.pathId}/modules/${wm.moduleId}`)}
                      >
                        Review Now
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          <Card>
            <SectionHeader title={t("learning_now")} subtitle={t("learning_now_desc")} />
            <div className="module-list">
              {learning.map(({ p, e, prog }) => {
                const next = nextModule(p, e);
                return (
                  <div className="module-row" key={p.id}>
                    <div className="module-icon">{prog.complete ? <CircleCheck size={17} /> : <RouteIcon size={17} />}</div>
                    <div className="module-info">
                      <strong>{pick(p, "title")} {e.source === "self" && <Badge tone="blue">{t("explore_status_self")}</Badge>}</strong>
                      <span>{next ? t("next_up", { stage: t(`stage_${next.stage.key}`), module: pick(next.module, "title") }) : t("path_completed")}</span>
                      {e.dueDate && !prog.complete && (
                        <span className={`learning-due ${e.overdue ? "is-overdue" : ""}`}>
                          {t(e.overdue ? "due_overdue" : "due_on", { date: date(e.dueDate) })}
                        </span>
                      )}
                      <ProgressBar value={prog.percent} showValue />
                    </div>
                    {prog.complete ? (
                      <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                        <Badge tone="green">{t("completed")}</Badge>
                        <Button variant="secondary" icon={<Award size={14} />} onClick={() => setCertPath({ p, e })}>
                          {t("certificate")}
                        </Button>
                      </div>
                    ) : (
                      <Button variant="secondary" icon={<Play size={14} />}
                        onClick={() => navigate(next ? `/employee/paths/${p.id}/modules/${next.module.id}` : `/employee/paths/${p.id}`)}>
                        {e.startedAt ? t("continue_learning_btn") : t("start_learning")}
                      </Button>
                    )}
                    <Button variant="ghost" onClick={() => navigate(`/employee/paths/${p.id}`)}><ArrowUpRight size={15} /></Button>
                  </div>
                );
              })}
            </div>
          </Card>
        </>
      )}

      {certPath && (
        <CertificateModal
          path={certPath.p}
          enrollment={certPath.e}
          onClose={() => setCertPath(null)}
        />
      )}
    </div>
  );
}
