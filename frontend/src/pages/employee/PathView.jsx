import { useNavigate, useParams } from "react-router-dom";
import { ArrowLeft, Check, LockKeyhole, BookOpen, ClipboardCheck, CheckSquare, ArrowUpRight } from "../../components/Icons";
import { Card, Badge, ProgressBar, EmptyState, Button } from "../../components/UI";
import { useLanguage } from "../../contexts/LanguageContext";
import { useEnrollment } from "../../contexts/EnrollmentContext";
import { useMyPaths } from "../../hooks/useMyPaths";
import { moduleProgress, pathProgress, stageUnlocked } from "../../utils/progress";

/** Lộ trình của nhân viên: các giai đoạn theo thứ tự, giai đoạn sau mở khi hoàn thành giai đoạn trước */
export default function PathView() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { t, tv, pick } = useLanguage();
  const { enrollmentFor } = useEnrollment();
  const path = useMyPaths().find(p => p.id === id);

  if (!path) {
    return <EmptyState title={t("err_path_not_found")} description={t("path_not_assigned")} action={<Button onClick={() => navigate("/employee/paths")}>{t("back_to_list")}</Button>} />;
  }
  const e = enrollmentFor(path.id);
  const prog = pathProgress(path, e);

  return (
    <div>
      <button className="back-btn" onClick={() => navigate("/employee/paths")}><ArrowLeft size={16} /> {t("back_to_list")}</button>
      <div className="page-heading">
        <div>
          <span className="eyebrow">{t(`purpose_${path.purpose}`)} · {tv(path.level)}</span>
          <h1>{pick(path, "title")}</h1>
          <p>{t("path_view_desc")}</p>
        </div>
        <Badge tone={prog.complete ? "green" : "purple"}>{t("percent_complete", { n: prog.percent })}</Badge>
      </div>
      <Card style={{ marginBottom: 18 }}><ProgressBar value={prog.percent} showValue /></Card>

      <div className="timeline">
        {path.stages.map((stage, si) => {
          const unlocked = stageUnlocked(path, si, e);
          const done = stage.modules.every(m => moduleProgress(m, e).complete);
          return (
            <div className={`timeline-item ${done ? "completed" : unlocked ? "active" : "locked"}`} key={stage.key}>
              <div className="timeline-marker">{done ? <Check size={17} /> : unlocked ? si + 1 : <LockKeyhole size={15} />}</div>
              <Card>
                <div className="stage-view__head">
                  <div>
                    <span className="eyebrow">{t("stage_n", { n: si + 1 })}</span>
                    <h3>{t(`stage_${stage.key}`)}</h3>
                  </div>
                  {!unlocked && <span className="cell-sub">{t("stage_locked_hint")}</span>}
                </div>
                <div className="stage-modules">
                  {stage.modules.map(m => {
                    const mp = moduleProgress(m, e);
                    return (
                      <button key={m.id} className={`stage-module ${mp.complete ? "is-done" : ""}`} disabled={!unlocked}
                        onClick={() => navigate(`/employee/paths/${path.id}/modules/${m.id}`)}>
                        <div>
                          <strong>{pick(m, "title")}</strong>
                          <span className="cell-sub">
                            {m.lessons.length > 0 && <><BookOpen size={11} /> {mp.lessonsDone}/{m.lessons.length} </>}
                            {m.tasks.length > 0 && <><CheckSquare size={11} /> {mp.tasksDone}/{m.tasks.length} </>}
                            {m.quiz.length > 0 && <><ClipboardCheck size={11} /> {mp.best ? `${mp.best.score}/${mp.best.total}` : t("quiz_not_taken")}</>}
                          </span>
                          <ProgressBar value={mp.percent} />
                        </div>
                        {mp.complete ? <Badge tone="green">{t("completed")}</Badge> : <ArrowUpRight size={16} />}
                      </button>
                    );
                  })}
                </div>
              </Card>
            </div>
          );
        })}
      </div>
    </div>
  );
}
