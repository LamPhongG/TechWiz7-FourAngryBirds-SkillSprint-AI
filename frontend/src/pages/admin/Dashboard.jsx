import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import {
  UserRound, ShieldCheck, CircleCheck, CircleAlert,
  ArrowUpRight, Plus, Building2, BriefcaseBusiness
} from "../../components/Icons";
import { Card, SectionHeader, StatCard, Button, Badge } from "../../components/UI";
import { useLanguage } from "../../contexts/LanguageContext";
import { useAuth } from "../../hooks/useAuth";
import { apiRequest } from "../../services/apiClient";
import { mapUser } from "../../services/apiMappers";
import { DEPARTMENTS } from "../../data/company";

const ROLE_COLORS = {
  admin: { name: "Admin", color: "#8b5cf6", bg: "#f3e8ff" },
  hr: { name: "HR", color: "#e11d48", bg: "#ffe4e6" },
  reviewer: { name: "Reviewer", color: "#d97706", bg: "#fef3c7" },
  employee: { name: "Employee", color: "#10b981", bg: "#d1fae5" },
};

export default function AdminDashboard() {
  const navigate = useNavigate();
  const { t, tv } = useLanguage();
  const { user } = useAuth();
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadUsers() {
      try {
        setLoading(true);
        const data = await apiRequest("/users");
        setUsers((data || []).map(mapUser));
      } catch (err) {
        console.error("Failed to load users for dashboard:", err);
      } finally {
        setLoading(false);
      }
    }
    loadUsers();
  }, []);

  const totalUsers = users.length;
  const activeUsers = users.filter(u => u.is_active).length;
  const inactiveUsers = users.filter(u => !u.is_active).length;

  const roleCounts = {
    admin: users.filter(u => u.userRole === "admin").length,
    hr: users.filter(u => u.userRole === "hr").length,
    reviewer: users.filter(u => u.userRole === "reviewer").length,
    employee: users.filter(u => u.userRole === "employee").length,
  };

  const recentUsers = users.slice(0, 5);

  return (
    <div>
      <div className="page-heading">
        <div>
          <span className="eyebrow">{t("role_admin")}</span>
          <h1>{t("dashboard_greeting", { name: user.name.split(" ")[0] })}</h1>
          <p>{t("admin_dashboard_desc")}</p>
        </div>
        <div className="heading-actions">
          <Button onClick={() => navigate("/admin/users")} icon={<UserRound size={16} />}>
            {t("menu_users")}
          </Button>
        </div>
      </div>

      <div className="stat-grid">
        <StatCard
          label={t("admin_stat_total_users")}
          value={totalUsers}
          icon={UserRound}
          tone="blue"
        />
        <StatCard
          label={t("admin_stat_active_users")}
          value={activeUsers}
          icon={CircleCheck}
          tone="green"
        />
        <StatCard
          label={t("admin_stat_inactive_users")}
          value={inactiveUsers}
          icon={CircleAlert}
          tone="red"
        />
        <StatCard
          label={t("admin_stat_roles")}
          value={Object.keys(ROLE_COLORS).length}
          icon={ShieldCheck}
          tone="orange"
        />
      </div>

      <div className="dashboard-grid">
        {/* 4 Roles Distribution */}
        <Card>
          <SectionHeader
            title={t("admin_role_distribution")}
            subtitle={t("admin_role_distribution_desc")}
          />
          <div style={{ display: "grid", gap: "12px", marginTop: "10px" }}>
            {Object.entries(roleCounts).map(([roleKey, count]) => {
              const cfg = ROLE_COLORS[roleKey];
              const pct = totalUsers ? Math.round((count / totalUsers) * 100) : 0;
              return (
                <div
                  key={roleKey}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    padding: "12px 14px",
                    background: "#f8fafc",
                    borderRadius: "8px",
                    border: "1px solid var(--line)",
                  }}
                >
                  <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                    <span
                      style={{
                        width: "12px",
                        height: "12px",
                        borderRadius: "50%",
                        background: cfg.color,
                      }}
                    />
                    <div>
                      <strong style={{ display: "block", fontSize: "14px" }}>
                        {t(`role_${roleKey}`)}
                      </strong>
                      <span style={{ fontSize: "12px", color: "var(--muted)" }}>
                        {t(`admin_role_desc_${roleKey}`)}
                      </span>
                    </div>
                  </div>
                  <div style={{ textAlign: "right" }}>
                    <strong style={{ fontSize: "16px", color: cfg.color }}>{count}</strong>
                    <div style={{ fontSize: "12px", color: "var(--muted)" }}>{pct}%</div>
                  </div>
                </div>
              );
            })}
          </div>
        </Card>

        {/* Department Distribution */}
        <Card>
          <SectionHeader
            title={t("admin_distribution_dept")}
            subtitle={t("admin_distribution_dept_desc")}
          />
          <div style={{ display: "grid", gap: "8px", maxHeight: "310px", overflowY: "auto", paddingRight: "4px" }}>
            {DEPARTMENTS.map(dept => {
              const count = users.filter(u => u.department === dept).length;
              if (count === 0) return null;
              return (
                <div
                  key={dept}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    padding: "10px 12px",
                    borderBottom: "1px solid var(--line)",
                    fontSize: "13px",
                  }}
                >
                  <span style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                    <Building2 size={15} style={{ color: "var(--muted)" }} />
                    <strong>{tv(dept)}</strong>
                  </span>
                  <Badge tone="blue">{t("admin_people", { n: count })}</Badge>
                </div>
              );
            })}
          </div>
        </Card>
      </div>

      {/* Recent Users List */}
      <Card style={{ marginTop: "20px" }}>
        <SectionHeader
          title={t("admin_recent_users")}
          subtitle={t("admin_recent_users_desc")}
          action={
            <Button variant="ghost" onClick={() => navigate("/admin/users")}>
              {t("view_all")} <ArrowUpRight size={14} />
            </Button>
          }
        />
        {recentUsers.length === 0 ? (
          <p className="cell-sub">{t(loading ? "admin_loading" : "admin_no_users")}</p>
        ) : (
          <div className="focus-list">
            {recentUsers.map(u => {
              const roleCfg = ROLE_COLORS[u.userRole] || ROLE_COLORS.employee;
              return (
                <div
                  key={u.id}
                  className="focus-item"
                  style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}
                >
                  <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                    <div
                      className="avatar"
                      style={{
                        width: "32px",
                        height: "32px",
                        borderRadius: "50%",
                        background: roleCfg.bg,
                        color: roleCfg.color,
                        display: "grid",
                        placeItems: "center",
                        fontSize: "12px",
                        fontWeight: 700,
                      }}
                    >
                      {u.avatar || u.name?.slice(0, 2).toUpperCase()}
                    </div>
                    <div>
                      <strong>{u.name}</strong>
                      <span style={{ marginLeft: "8px", fontSize: "12px", color: "var(--muted)" }}>
                        {u.email} · {tv(u.department || "Company-wide")}
                      </span>
                    </div>
                  </div>
                  <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                    <Badge tone={u.userRole === "admin" ? "purple" : u.userRole === "hr" ? "red" : u.userRole === "reviewer" ? "orange" : "green"}>
                      {t(`role_${u.userRole}`)}
                    </Badge>
                    {u.is_active ? (
                      <Badge tone="green">{t("user_status_active")}</Badge>
                    ) : (
                      <Badge tone="red">{t("user_status_inactive")}</Badge>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </Card>
    </div>
  );
}
