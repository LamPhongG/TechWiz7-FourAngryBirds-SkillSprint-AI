import { Mail, BriefcaseBusiness, Building2 } from "../../components/Icons";
import { Card, SectionHeader, Badge } from "../../components/UI";
import { useLanguage } from "../../contexts/LanguageContext";
import { useEnrollment } from "../../contexts/EnrollmentContext";
import { useAuth } from "../../hooks/useAuth";
import { ROLES as JOB_ROLES } from "../../data/company";
import { useMyPaths } from "../../hooks/useMyPaths";
import { bestAttempt, pathProgress, PASS_RATIO } from "../../utils/progress";
import { formatDateTime } from "../../utils/helpers";

export default function Profile() {
  const { t, tv, pick, locale } = useLanguage();
  const { user, setEmployeePosition } = useAuth();
  const { enrollmentFor } = useEnrollment();
  const myPaths = useMyPaths();
  const job = JOB_ROLES.find(r => r.id === user.role_id);

  const attempts = myPaths.flatMap(p => p.stages.flatMap(s => s.modules.filter(m => m.quiz.length).map(m => ({ p, m, best: bestAttempt(enrollmentFor(p.id), m.id) })))).filter(x => x.best);

  return (
    <div>
      <div className="page-heading">
        <div><span className="eyebrow">{t("menu_profile")}</span><h1>{user.name}</h1><p>{pick(job, "name")}</p></div>
      </div>
      <div className="run-grid" style={{ marginBottom: 18 }}>
        <Card>
          <SectionHeader title={t("profile_info")} />
          <dl className="meta-list">
            <dt><BriefcaseBusiness size={14} /> {t("role_position")}</dt><dd>{pick(job, "name")}</dd>
            <dt><Building2 size={14} /> {t("department")}</dt><dd>{tv(user.department)}</dd>
            <dt><Mail size={14} /> Email</dt><dd>alex.morgan@fourangrybirds.vn</dd>
          </dl>
        </Card>
        <Card>
          <SectionHeader title={t("demo_position_title")} subtitle={t("demo_position_desc")} />
          <select className="filter-select" style={{ width: "100%" }} value={user.role_id} onChange={e => setEmployeePosition(e.target.value)}>
            {JOB_ROLES.map(r => <option key={r.id} value={r.id}>{pick(r, "name")} · {tv(r.department)}</option>)}
          </select>
        </Card>
      </div>

      <Card style={{ marginBottom: 18 }}>
        <SectionHeader title={t("menu_my_paths")} />
        {myPaths.length === 0 ? <p className="cell-sub">{t("no_assigned_paths_desc", { department: tv(user.department) })}</p> : (
          <ul className="dept-list">
            {myPaths.map(p => {
              const e = enrollmentFor(p.id);
              const prog = pathProgress(p, e);
              return (
                <li key={p.id}>
                  <strong>{pick(p, "title")}</strong>
                  <span>
                    <Badge tone={prog.complete ? "green" : "purple"}>{prog.percent}%</Badge>
                    {e.completedAt && <span className="cell-sub">{t("completed_on", { date: formatDateTime(e.completedAt, locale) })}</span>}
                  </span>
                </li>
              );
            })}
          </ul>
        )}
      </Card>

      <Card>
        <SectionHeader title={t("quiz_history")} />
        {attempts.length === 0 ? <p className="cell-sub">{t("quiz_history_empty")}</p> : (
          <div className="table-wrap">
            <table>
              <thead><tr><th>{t("col_module")}</th><th>{t("col_path")}</th><th>{t("best_score_col")}</th><th>{t("col_updated")}</th></tr></thead>
              <tbody>
                {attempts.map(({ p, m, best }) => (
                  <tr key={m.id}>
                    <td>{pick(m, "title")}</td>
                    <td>{pick(p, "title")}</td>
                    <td><Badge tone={best.score / best.total >= PASS_RATIO ? "green" : "red"}>{best.score}/{best.total}</Badge></td>
                    <td>{formatDateTime(best.at, locale)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}
