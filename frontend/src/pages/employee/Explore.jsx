import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowUpRight, CircleAlert, Compass, Eye, Plus, RouteIcon } from "../../components/Icons";
import { Badge, Button, Card, EmptyState, Modal, ProgressBar, Toast } from "../../components/UI";
import { useLanguage } from "../../contexts/LanguageContext";
import { useEnrollment } from "../../contexts/EnrollmentContext";
import { useAuth } from "../../hooks/useAuth";
import { apiRequest, backendEnabled } from "../../services/apiClient";
import { formatLocalDate } from "../../utils/helpers";

const STATUS_KEY = { assigned: "not_started", in_progress: "in_progress", completed: "completed" };

/**
 * Explore learning paths: all published paths for the employee's department (including other roles),
 * to preview upcoming learning requirements or self-enroll in optional paths.
 */
export default function Explore() {
  const navigate = useNavigate();
  const { t, tv, lang, locale } = useLanguage();
  const { user } = useAuth();
  const { enroll } = useEnrollment();
  const [paths, setPaths] = useState(null);
  const [error, setError] = useState("");
  const [preview, setPreview] = useState(null);
  const [busyId, setBusyId] = useState(null);
  const [toast, setToast] = useState("");

  const load = useCallback(async () => {
    try {
      setPaths(await apiRequest("/explore/paths"));
    } catch (e) {
      setError(e.code || "err_network");
    }
  }, []);

  useEffect(() => { if (backendEnabled()) load(); }, [load]);

  if (!backendEnabled()) {
    return <Card><EmptyState title={t("menu_explore")} description={t("explore_needs_backend")} /></Card>;
  }

  const title = p => (lang === "en" ? p.title_en : p.title);

  const openPreview = async path => {
    setPreview({ ...path, outline: null });
    try {
      setPreview(await apiRequest(`/explore/paths/${encodeURIComponent(path.id)}`));
    } catch (e) {
      setPreview(null);
      setToast(t(e.code || "err_network"));
    }
  };

  const join = async path => {
    setBusyId(path.id);
    try {
      await enroll(path.id);
      setToast(t("explore_enrolled"));
      setPreview(null);
      await load();
    } catch (e) {
      setToast(t(e.code || "err_network"));
    } finally {
      setBusyId(null);
    }
  };

  const actions = path => (path.enrollment ? (
    <Button onClick={() => navigate(`/employee/paths/${path.id}`)} icon={<ArrowUpRight size={15} />}>{t("explore_open")}</Button>
  ) : (
    <Button onClick={() => join(path)} disabled={busyId === path.id} icon={<Plus size={15} />}>
      {t(busyId === path.id ? "explore_enrolling" : "explore_enroll")}
    </Button>
  ));

  return (
    <div>
      <div className="page-heading">
        <div>
          <span className="eyebrow">{tv(user.department)}</span>
          <h1>{t("menu_explore")}</h1>
          <p>{t("explore_desc", { department: tv(user.department) })}</p>
        </div>
      </div>

      {error && <div className="notice notice--danger"><CircleAlert size={16} /><span>{t(error)}</span></div>}
      {paths && paths.length === 0 && (
        <Card><EmptyState title={t("menu_explore")} description={t("explore_empty", { department: tv(user.department) })} /></Card>
      )}

      <div className="path-grid">
        {(paths || []).map(p => (
          <Card key={p.id} className="path-card">
            <div className="card-title-row">
              <div className="module-icon"><RouteIcon size={17} /></div>
              <span className="explore-badges">
                {p.for_my_position && <Badge tone="purple">{t("explore_for_my_position")}</Badge>}
                {p.enrollment && (
                  <Badge tone={p.enrollment.status === "completed" ? "green" : "blue"}>
                    {t(p.enrollment.source === "self" ? "explore_status_self" : "explore_status_assigned")}
                  </Badge>
                )}
              </span>
            </div>
            <h3>{title(p)}</h3>
            <p className="cell-sub">{t(`purpose_${p.purpose}`)} · {tv(p.level)}</p>
            <p className="cell-sub">
              {t("explore_stats", { stages: p.stages, modules: p.modules, lessons: p.lessons })}
              {p.minutes > 0 && <> · {t("explore_minutes", { n: p.minutes })}</>}
            </p>
            {p.enrollment && (
              <>
                <p className="cell-sub">
                  {t(STATUS_KEY[p.enrollment.status])}
                  {p.enrollment.due_date && <> · {t("due_on", { date: formatLocalDate(p.enrollment.due_date, locale, { day: "2-digit", month: "2-digit", year: "numeric" }) })}</>}
                </p>
                <ProgressBar value={p.enrollment.percent} showValue />
              </>
            )}
            <div className="explore-actions">
              <Button variant="secondary" onClick={() => openPreview(p)} icon={<Eye size={15} />}>{t("explore_preview")}</Button>
              {actions(p)}
            </div>
          </Card>
        ))}
      </div>

      <Modal open={!!preview} title={preview ? title(preview) : ""} onClose={() => setPreview(null)} width="720px">
        {preview && !preview.outline && <p className="cell-sub">{t("explore_loading")}</p>}
        {preview?.outline && (
          <>
            <p className="cell-sub">{t("explore_preview_note")}</p>
            {preview.outline.map(stage => (
              <div key={stage.key} className="explore-stage">
                <h4><Compass size={14} /> {t(`stage_${stage.key}`)}</h4>
                {stage.modules.map(m => (
                  <div key={m.id} className="explore-module">
                    <strong>{lang === "en" && m.title_en ? m.title_en : m.title}</strong>
                    <span className="cell-sub">
                      {m.doc_code && <>{m.doc_code} · </>}
                      {t("explore_module_counts", { l: m.lessons.length, t: m.tasks, q: m.questions })}
                    </span>
                    {m.lessons.length > 0 && <ul>{m.lessons.map((l, i) => <li key={i}>{l || t("explore_untitled_lesson")}</li>)}</ul>}
                  </div>
                ))}
              </div>
            ))}
            <div className="modal-actions">
              <Button variant="secondary" onClick={() => setPreview(null)}>{t("explore_close")}</Button>
              {actions(preview)}
            </div>
          </>
        )}
      </Modal>
      <Toast message={toast} onClose={() => setToast("")} />
    </div>
  );
}
