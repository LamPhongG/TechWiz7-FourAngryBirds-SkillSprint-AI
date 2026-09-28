import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { RouteIcon, ArrowUpRight, Award } from "../../components/Icons";
import { Card, Badge, ProgressBar, EmptyState, Button } from "../../components/UI";
import { useLanguage } from "../../contexts/LanguageContext";
import { useEnrollment } from "../../contexts/EnrollmentContext";
import { useAuth } from "../../hooks/useAuth";
import { useMyPaths } from "../../hooks/useMyPaths";
import { usePaths } from "../../contexts/PathsContext";
import { pathProgress } from "../../utils/progress";
import { formatDateTime, formatLocalDate } from "../../utils/helpers";
import CertificateModal from "../../components/path/CertificateModal";

export default function MyPaths() {
  const navigate = useNavigate();
  const { t, tv, pick, locale } = useLanguage();
  const { user } = useAuth();
  const { enrollmentFor } = useEnrollment();
  const myPaths = useMyPaths();
  const { loaded } = usePaths();
  const [certPath, setCertPath] = useState(null);

  return (
    <div>
      <div className="page-heading">
        <div>
          <span className="eyebrow">{tv(user.department)} · {user.role}</span>
          <h1>{t("menu_my_paths")}</h1>
          <p>{t("my_paths_desc")}</p>
        </div>
      </div>
      {!loaded ? (
        <Card><p className="cell-sub">{t("explore_loading")}</p></Card>
      ) : myPaths.length === 0 ? (
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
                <h3>{pick(p, "title")} {e.source === "self" && <Badge tone="blue">{t("explore_status_self")}</Badge>}</h3>
                <p className="cell-sub">{t(`purpose_${p.purpose}`)} · {tv(p.level)} · {t("stages_modules", { s: p.stages.length, m: prog.total })}</p>
                <p className="cell-sub">{t("published_on", { date: formatDateTime(p.published_at, locale) })}</p>
                {e.dueDate && !prog.complete && (
                  <p className={e.overdue ? "text-danger" : "cell-sub"}>
                    {t(e.overdue ? "due_overdue" : "due_on", { date: formatLocalDate(e.dueDate, locale, { day: "2-digit", month: "2-digit", year: "numeric" }) })}
                  </p>
                )}
                <ProgressBar value={prog.percent} showValue />
                <div style={{ display: "flex", gap: 8, marginTop: 12 }}>
                  <Button variant="secondary" onClick={() => navigate(`/employee/paths/${p.id}`)}>
                    {t("open")} <ArrowUpRight size={14} />
                  </Button>
                  {prog.complete && (
                    <Button variant="outline" onClick={() => setCertPath({ path: p, enrollment: e })}>
                      <Award size={14} /> {t("certificate")}
                    </Button>
                  )}
                </div>
              </Card>
            );
          })}
        </div>
      )}
      
      {certPath && (
        <CertificateModal
          path={certPath.path}
          employee={user}
          enrollment={certPath.enrollment}
          onClose={() => setCertPath(null)}
        />
      )}
    </div>
  );
}
