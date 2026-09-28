import { useState, useEffect, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import {
  Users, Award, Search, RouteIcon, BookOpen, CheckSquare,
  ArrowUpRight, Download, Clock, ShieldCheck, CircleAlert
} from "../../components/Icons";
import { Card, SectionHeader, StatCard, Button, Badge, ProgressBar, EmptyState } from "../../components/UI";
import { useLanguage } from "../../contexts/LanguageContext";
import { useAuth } from "../../hooks/useAuth";
import { usePaths } from "../../contexts/PathsContext";
import { apiRequest, backendEnabled } from "../../services/apiClient";
import { DEPARTMENTS } from "../../data/company";
import { formatLocalDate } from "../../utils/helpers";
import CertificateModal from "../../components/path/CertificateModal";

export default function HrLearners() {
  const navigate = useNavigate();
  const { t, tv, pick, locale } = useLanguage();
  const { user } = useAuth();
  const { paths } = usePaths();

  const [learners, setLearners] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [selectedDept, setSelectedDept] = useState("all");
  const [selectedStatus, setSelectedStatus] = useState("all");
  const [selectedCert, setSelectedCert] = useState(null);

  const fetchLearners = async () => {
    setLoading(true);
    try {
      if (backendEnabled()) {
        const data = await apiRequest("/learners");
        setLearners(data || []);
      } else {
        setLearners([]);
      }
    } catch (err) {
      console.error("Failed to fetch learners:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLearners();
  }, [paths]);

  const stats = useMemo(() => {
    const total = learners.length;
    const completed = learners.filter(l => l.status === "completed" || l.percent === 100).length;
    const overdue = learners.filter(l => l.overdue && l.status !== "completed").length;
    const onTrack = learners.filter(l => (l.status === "in_progress" || l.status === "assigned") && !l.overdue).length;
    return { total, completed, overdue, onTrack };
  }, [learners]);

  const filtered = useMemo(() => {
    return learners.filter(l => {
      const name = l.name;
      const email = l.email;
      const pathTitle = l.path_title || "";
      const dept = l.department_code || "";
      const percent = l.percent;
      const isOverdue = l.overdue;

      const q = search.trim().toLowerCase();
      const matchSearch = !q ||
        name.toLowerCase().includes(q) ||
        email.toLowerCase().includes(q) ||
        pathTitle.toLowerCase().includes(q);
      
      const matchDept = selectedDept === "all" || dept === selectedDept;
      
      let matchStatus = true;
      if (selectedStatus === "completed") {
        matchStatus = l.status === "completed" || percent === 100;
      } else if (selectedStatus === "in_progress") {
        matchStatus = (l.status === "in_progress" || l.status === "assigned") && !isOverdue && percent < 100;
      } else if (selectedStatus === "overdue") {
        matchStatus = isOverdue && l.status !== "completed";
      } else if (selectedStatus === "not_started") {
        matchStatus = !l.started_at && l.status !== "completed";
      }

      return matchSearch && matchDept && matchStatus;
    });
  }, [learners, search, selectedDept, selectedStatus]);

  const dateStr = iso => iso ? formatLocalDate(iso, locale, { day: "2-digit", month: "2-digit", year: "numeric" }) : "—";

  return (
    <div>
      <div className="page-heading">
        <div>
          <span className="eyebrow">{t("role_hr")}</span>
          <h1>{t("learners_title")}</h1>
          <p>{t("learners_desc")}</p>
        </div>
      </div>
      
      {!backendEnabled() ? (
        <EmptyState title={t("reports_need_backend")} description="" />
      ) : (
        <>
      <div className="stat-grid">
        <StatCard label={t("stat_total_learners")} value={stats.total} icon={Users} tone="purple" />
        <StatCard label={t("stat_completed_learners")} value={stats.completed} icon={Award} tone="green" />
        <StatCard label={t("stat_on_track")} value={stats.onTrack} icon={CheckSquare} tone="blue" />
        <StatCard label={t("stat_overdue")} value={stats.overdue} icon={CircleAlert} tone={stats.overdue > 0 ? "red" : "orange"} />
      </div>

      <Card style={{ marginBottom: "20px" }}>
        <div style={{ display: "flex", gap: "12px", flexWrap: "wrap", alignItems: "center", justifyContent: "space-between" }}>
          <div style={{ display: "flex", gap: "10px", flexWrap: "wrap", flex: 1, minWidth: "280px" }}>
            <div className="search-input" style={{ minWidth: "240px", flex: 1 }}>
              <Search size={16} />
              <input
                value={search}
                onChange={e => setSearch(e.target.value)}
                placeholder={t("learners_search_placeholder")}
              />
            </div>

            <select
              className="filter-select"
              value={selectedDept}
              onChange={e => setSelectedDept(e.target.value)}
            >
              <option value="all">{t("filter_department_all")}</option>
              {DEPARTMENTS.map(d => (
                <option key={d} value={d}>{tv(d)}</option>
              ))}
            </select>

            <select
              className="filter-select"
              value={selectedStatus}
              onChange={e => setSelectedStatus(e.target.value)}
            >
              <option value="all">{t("user_filter_all_statuses")}</option>
              <option value="completed">{t("completed")}</option>
              <option value="in_progress">{t("learning_in_progress")}</option>
              <option value="overdue">{t("due_overdue_badge")}</option>
              <option value="not_started">{t("not_started")}</option>
            </select>
          </div>

          <div style={{ fontSize: "13px", color: "var(--muted)", fontWeight: 500 }}>
            {t("user_total_count", { n: filtered.length })}
          </div>
        </div>
      </Card>

      <Card>
        {loading ? (
          <div style={{ padding: "40px", textAlign: "center", color: "var(--muted)" }}>
            {t("explore_loading")}
          </div>
        ) : filtered.length === 0 ? (
          <div style={{ padding: "40px", textAlign: "center", color: "var(--muted)" }}>
            {t("no_learners_found")}
          </div>
        ) : (
          <div style={{ overflowX: "auto" }}>
            <table className="data-table" style={{ width: "100%", borderCollapse: "collapse" }}>
              <thead>
                <tr style={{ borderBottom: "1px solid var(--border)", textAlign: "left" }}>
                  <th style={{ padding: "12px 16px" }}>{t("table_col_employee")}</th>
                  <th style={{ padding: "12px 16px" }}>{t("department")}</th>
                  <th style={{ padding: "12px 16px" }}>{t("table_col_path")}</th>
                  <th style={{ padding: "12px 16px", minWidth: "160px" }}>{t("table_col_progress")}</th>
                  <th style={{ padding: "12px 16px" }}>{t("status")}</th>
                  <th style={{ padding: "12px 16px", textAlign: "right" }}>{t("table_col_actions")}</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map(l => {
                  const empName = l.name;
                  const empEmail = l.email;
                  const empDept = l.department_code || "Company-wide";
                  const percent = l.percent;
                  const isOverdue = l.overdue;
                  const isDone = l.status === "completed" || percent === 100;

                  return (
                    <tr key={l.enrollment_id} style={{ borderBottom: "1px solid var(--border-light, #eee)" }}>
                      <td style={{ padding: "12px 16px" }}>
                        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                          <div style={{
                            width: "36px",
                            height: "36px",
                            borderRadius: "50%",
                            background: "var(--primary-light, rgba(99, 102, 241, 0.1))",
                            color: "var(--primary, #6366f1)",
                            display: "grid",
                            placeItems: "center",
                            fontWeight: 700,
                            fontSize: "14px",
                            flexShrink: 0
                          }}>
                            {empName.charAt(0).toUpperCase()}
                          </div>
                          <div>
                            <div style={{ fontWeight: 600, color: "var(--text)" }}>{empName}</div>
                            <div style={{ fontSize: "12px", color: "var(--muted)" }}>{empEmail}</div>
                          </div>
                        </div>
                      </td>
                      <td style={{ padding: "12px 16px" }}>
                        <Badge tone="purple">{tv(empDept)}</Badge>
                        {l.job_title && (
                          <div style={{ fontSize: "11px", color: "var(--muted)", marginTop: "4px" }}>
                            {l.job_title}
                          </div>
                        )}
                      </td>
                      <td style={{ padding: "12px 16px" }}>
                        <div style={{ fontWeight: 600, color: "var(--text)" }}>{l.path_title}</div>
                        <div style={{ fontSize: "12px", color: "var(--muted)", marginTop: "2px" }}>
                          {l.due_date ? t("due_on", { date: dateStr(l.due_date) }) : t("no_due_date")}
                        </div>
                      </td>
                      <td style={{ padding: "12px 16px" }}>
                        <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
                          <ProgressBar value={percent} showValue />
                        </div>
                      </td>
                      <td style={{ padding: "12px 16px" }}>
                        {isDone ? (
                          <Badge tone="green">{t("completed")}</Badge>
                        ) : isOverdue ? (
                          <Badge tone="red">{t("due_overdue_badge")}</Badge>
                        ) : l.started_at ? (
                          <Badge tone="blue">{t("learning_in_progress")}</Badge>
                        ) : (
                          <Badge tone="default">{t("not_started")}</Badge>
                        )}
                      </td>
                      <td style={{ padding: "12px 16px", textAlign: "right" }}>
                        <div style={{ display: "flex", gap: "8px", justifyContent: "flex-end" }}>
                          {isDone && (
                            <Button
                              variant="secondary"
                              size="sm"
                              icon={<Award size={14} />}
                              onClick={() => {
                                const matchedPath = paths.find(p => p.id === l.path_id) || {
                                  id: l.path_id,
                                  title: l.path_title,
                                  points: 100
                                };
                                setSelectedCert({
                                  employee: {
                                    id: l.user_id,
                                    name: empName,
                                    email: empEmail,
                                    employee_code: typeof l.user_id === "string" ? l.user_id : `EMP-${l.user_id}`
                                  },
                                  path: matchedPath,
                                  enrollment: {
                                    id: l.enrollment_id,
                                    completedAt: l.completed_at
                                  }
                                });
                              }}
                            >
                              {t("certificate")}
                            </Button>
                          )}
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => navigate(`/hr/paths/${l.path_id}`)}
                            title={t("view_path_details")}
                          >
                            <ArrowUpRight size={15} />
                          </Button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </Card>
      </>
      )}

      {selectedCert && (
        <CertificateModal
          employee={selectedCert.employee}
          path={selectedCert.path}
          enrollment={selectedCert.enrollment}
          onClose={() => setSelectedCert(null)}
        />
      )}
    </div>
  );
}
