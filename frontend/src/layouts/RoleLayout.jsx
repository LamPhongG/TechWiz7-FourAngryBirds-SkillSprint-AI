import { useState } from "react";
import { Outlet, NavLink, Navigate, useLocation, useNavigate } from "react-router-dom";
import { Compass,
  LayoutDashboard, RouteIcon, FileText, UserRound, Users, ShieldCheck, History, WandSparkles, Layers3,
  Menu, ChevronDown, LogOut, Sparkles, Link2, BarChart3
} from "../components/Icons";
import { useAuth, HOME_PATH } from "../hooks/useAuth";
import { useLanguage } from "../contexts/LanguageContext";
import { usePaths } from "../contexts/PathsContext";
import ErrorBoundary from "../components/ErrorBoundary";
import ChangePasswordModal from "../components/ChangePasswordModal";
import { Toast } from "../components/UI";
import { backendEnabled } from "../services/apiClient";

const ROLE_STYLE = {
  admin: { dot: "#8b5cf6", avatar: ["#ede9fe", "#7c3aed"] },
  employee: { dot: "#57d99e", avatar: ["#eae7ff", "#5a50c9"] },
  reviewer: { dot: "#f59e0b", avatar: ["#fef3c7", "#d97706"] },
  hr: { dot: "#f43f5e", avatar: ["#ffe4e6", "#e11d48"] },
};

// [locale key, route path, icon, pending count function]
function navFor(role, paths) {
  if (role === "admin") {
    return [
      ["menu_dashboard", "/admin/dashboard", LayoutDashboard],
      ["menu_users", "/admin/users", UserRound],
    ];
  }
  if (role === "hr") {
    return [
      ["menu_dashboard", "/hr/dashboard", LayoutDashboard],
      ["menu_documents", "/hr/documents", FileText],
      ["menu_create_path", "/hr/paths/new", WandSparkles],
      ["menu_paths", "/hr/paths", Layers3, paths.filter(p => p.status === "changes_requested").length],
      ["menu_learners", "/hr/learners", Users],
      ["menu_reports", "/hr/reports", BarChart3],
      ["menu_invites", "/hr/invites", Link2],
      ["menu_audit_log", "/hr/audit-log", History],
    ];
  }
  if (role === "reviewer") {
    return [
      ["menu_dashboard", "/reviewer/dashboard", LayoutDashboard],
      ["menu_review_queue", "/reviewer/queue", ShieldCheck, paths.filter(p => p.status === "in_review").length],
      ["menu_paths", "/reviewer/paths", Layers3],
      ["menu_audit_log", "/reviewer/audit-log", History],
    ];
  }
  return [
    ["menu_dashboard", "/employee/dashboard", LayoutDashboard],
    ["menu_my_paths", "/employee/paths", RouteIcon],
    ["menu_explore", "/employee/explore", Compass],
    ["menu_documents", "/employee/documents", FileText],
    ["menu_profile", "/employee/profile", UserRound],
  ];
}

/** Layout wrapper for a role; unauthenticated users or role mismatches are redirected */
export default function RoleLayout({ role }) {
  const [collapsed, setCollapsed] = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);
  const [passwordOpen, setPasswordOpen] = useState(false);
  const [toast, setToast] = useState(null);
  const location = useLocation();
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const { t } = useLanguage();
  const { paths } = usePaths();

  if (!user) return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  if (user.userRole !== role) return <Navigate to={HOME_PATH[user.userRole]} replace />;

  const nav = navFor(role, paths);
  const style = ROLE_STYLE[role];
  // Longest matching menu item so /hr/paths/new does not highlight /hr/paths
  const current = [...nav].sort((a, b) => b[1].length - a[1].length).find(([, to]) => location.pathname.startsWith(to));

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  return (
    <div className={`app-shell ${collapsed ? "sidebar-collapsed" : ""}`}>
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark" style={{ overflow: "hidden", padding: 0, border: "none", background: "transparent" }}>
            <img src="/logonhom.png" alt="Logo" style={{ height: "100%", width: "100%", objectFit: "cover", borderRadius: "8px" }} />
          </div>
          <span>SkillSprint AI</span>
        </div>
        <div className="role-switcher">
          <span className="role-dot" style={{ background: style.dot }} />
          <span>{t(`role_${role}`)}</span>
        </div>
        <nav className="sidebar-nav">
          <div className="nav-label">{t(`nav_${role}`)}</div>
          {nav.map(([key, to, Icon, count]) => (
            <NavLink key={to} to={to} end className={() => `nav-item ${current?.[1] === to ? "active" : ""}`}>
              <Icon size={18} /><span>{t(key)}</span>
              {count > 0 && <em className="nav-count">{count}</em>}
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <button className="nav-item nav-button" onClick={handleLogout}><LogOut size={18} /><span>{t("sign_out")}</span></button>
        </div>
      </aside>
      <main className="main">
        <header className="topbar">
          <button className="icon-btn mobile-menu" onClick={() => setCollapsed(v => !v)} aria-label="Menu"><Menu size={20} /></button>
          <div className="breadcrumbs">
            <span>{t(`role_${role}`)}</span><b>/</b>
            <strong>{current ? t(current[0]) : ""}</strong>
          </div>
          <div className="topbar-actions">
            <div className="profile" onClick={() => setProfileOpen(v => !v)}>
              <div className="avatar" style={{ background: style.avatar[0], color: style.avatar[1] }}>{user.avatar}</div>
              <div className="profile-text">
                <strong>{user.name}</strong>
                <span>{user.role}</span>
              </div>
              <ChevronDown size={15} />
              {profileOpen && (
                <div className="profile-menu">
                  {role === "employee" && <button onClick={() => navigate("/employee/profile")}>{t("menu_profile")}</button>}
                  {backendEnabled() && <button onClick={() => setPasswordOpen(true)}>{t("pwd_change")}</button>}
                  <button onClick={handleLogout}>{t("sign_out")}</button>
                </div>
              )}
            </div>
          </div>
        </header>
        <div className="content"><ErrorBoundary inline><Outlet /></ErrorBoundary></div>
        <ChangePasswordModal open={passwordOpen} onClose={() => setPasswordOpen(false)} onDone={setToast} />
        <Toast message={toast} onClose={() => setToast(null)} />
      </main>
    </div>
  );
}
