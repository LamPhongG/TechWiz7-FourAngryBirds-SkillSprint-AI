import { useNavigate } from "react-router-dom";
import { RouteIcon, ArrowUpRight } from "../../components/Icons";
import { Card, Badge, ProgressBar, EmptyState, Button } from "../../components/UI";
import { useLanguage } from "../../contexts/LanguageContext";
import { useEnrollment } from "../../contexts/EnrollmentContext";
import { useAuth } from "../../hooks/useAuth";
import { useMyPaths } from "../../hooks/useMyPaths";
import { pathProgress } from "../../utils/progress";
import { formatDateTime } from "../../utils/helpers";

export default function MyPaths() {
  const navigate = useNavigate();
  const { t, tv, pick, locale } = useLanguage();
  const { user } = useAuth();
  const { enrollmentFor } = useEnrollment();
  const myPaths = useMyPaths();

  return (
    <div>
      <div className="page-heading">
        <div>
          <span className="eyebrow">{tv(user.department)} · {user.role}</span>
          <h1>{t("menu_my_paths")}</h1>
          <p>{t("my_paths_desc")}</p>
        </div>
      </div>
      {myPaths.length === 0 ? (
        <Card><EmptyState title={t("no_assigned_paths")} description={t("no_assigned_paths_desc", { department: tv(user.department) })} /></Card>
      ) : (
        <div className="path-grid">
          {myPaths.map(p => {
            const e = enrollmentFor(p.id);
            const prog = pathProgress(p, e);
            return (
              <Card key={p.id} className="path-card">
                <div className="card-title-row">
                  <div className="module-icon"><RouteIcon size={17} /></div>
                  <Badge tone={prog.complete ? "green" : e.startedAt ? "purple" : "default"}>
                    {t(prog.complete ? "completed" : e.startedAt ? "in_progress" : "not_started")}
                  </Badge>
                </div>
                <h3>{pick(p, "title")}</h3>
                <p className="cell-sub">{t(`purpose_${p.purpose}`)} · {tv(p.level)} · {t("stages_modules", { s: p.stages.length, m: prog.total })}</p>
                <p className="cell-sub">{t("published_on", { date: formatDateTime(p.published_at, locale) })}</p>
                <ProgressBar value={prog.percent} showValue />
                <Button variant="secondary" onClick={() => navigate(`/employee/paths/${p.id}`)} style={{ marginTop: 12 }}>
                  {t("open")} <ArrowUpRight size={14} />
                </Button>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}
