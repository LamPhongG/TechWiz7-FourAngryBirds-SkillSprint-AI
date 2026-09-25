import { Routes, Route, Navigate, Link } from "react-router-dom";
import { AuthContext, useAuthProvider, HOME_PATH } from "./hooks/useAuth";
import { LanguageProvider, useLanguage } from "./contexts/LanguageContext";
import { DocumentsProvider } from "./contexts/DocumentsContext";
import { PathsProvider } from "./contexts/PathsContext";
import { EnrollmentProvider } from "./contexts/EnrollmentContext";

import AuthLayout from "./layouts/AuthLayout";
import RoleLayout from "./layouts/RoleLayout";

import Login from "./pages/auth/Login";

import HrDashboard from "./pages/hr/Dashboard";
import HrDocuments from "./pages/hr/Documents";
import CreatePath from "./pages/hr/CreatePath";

import ReviewerDashboard from "./pages/reviewer/Dashboard";

import PathList from "./pages/shared/PathList";
import PathDetail from "./pages/shared/PathDetail";
import AuditLog from "./pages/shared/AuditLog";

import EmployeeDashboard from "./pages/employee/Dashboard";
import MyPaths from "./pages/employee/MyPaths";
import PathView from "./pages/employee/PathView";
import ModuleView from "./pages/employee/ModuleView";
import EmployeeDocuments from "./pages/employee/Documents";
import Profile from "./pages/employee/Profile";

function NotFound({ user }) {
  const { t } = useLanguage();
  return (
    <div className="page-empty">
      <div style={{ textAlign: "center" }}>
        <div className="empty-icon">404</div>
        <h2>{t("page_not_found")}</h2>
        <p style={{ color: "var(--muted)" }}>{t("page_not_found_desc")}</p>
        <Link className="btn btn-primary" to={user ? HOME_PATH[user.userRole] : "/login"}>{t(user ? "go_home" : "crash_login")}</Link>
      </div>
    </div>
  );
}

function HrPaths() {
  const { t } = useLanguage();
  return (
    <PathList basePath="/hr/paths" createPath="/hr/paths/new"
      tabs={["all", "draft", "in_review", "changes_requested", "published", "archived"]}
      eyebrow={t("role_hr")} title={t("menu_paths")} description={t("hr_paths_desc")} />
  );
}

function ReviewerQueue() {
  const { t } = useLanguage();
  return (
    <PathList basePath="/reviewer/paths" tabs={["in_review"]}
      eyebrow={t("review_queue_eyebrow")} title={t("menu_review_queue")} description={t("review_queue_desc")} />
  );
}

function ReviewerPaths() {
  const { t } = useLanguage();
  return (
    <PathList basePath="/reviewer/paths" tabs={["all", "in_review", "changes_requested", "published", "archived"]}
      eyebrow={t("role_reviewer")} title={t("menu_paths")} description={t("reviewer_paths_desc")} />
  );
}

export default function App() {
  const auth = useAuthProvider();

  return (
    <LanguageProvider>
      <AuthContext.Provider value={auth}>
        <DocumentsProvider>
            <PathsProvider>
              <EnrollmentProvider>
                <Routes>
                  <Route element={<AuthLayout />}>
                    <Route path="/login" element={<Login />} />
                  </Route>

                  <Route path="/hr" element={<RoleLayout role="hr" />}>
                    <Route index element={<Navigate to="/hr/dashboard" replace />} />
                    <Route path="dashboard" element={<HrDashboard />} />
                    <Route path="documents" element={<HrDocuments />} />
                    <Route path="paths" element={<HrPaths />} />
                    <Route path="paths/new" element={<CreatePath />} />
                    <Route path="paths/:id" element={<PathDetail basePath="/hr/paths" />} />
                    <Route path="audit-log" element={<AuditLog pathBasePath="/hr/paths" />} />
                  </Route>

                  <Route path="/reviewer" element={<RoleLayout role="reviewer" />}>
                    <Route index element={<Navigate to="/reviewer/dashboard" replace />} />
                    <Route path="dashboard" element={<ReviewerDashboard />} />
                    <Route path="queue" element={<ReviewerQueue />} />
                    <Route path="paths" element={<ReviewerPaths />} />
                    <Route path="paths/:id" element={<PathDetail basePath="/reviewer/paths" />} />
                    <Route path="audit-log" element={<AuditLog pathBasePath="/reviewer/paths" />} />
                  </Route>

                  <Route path="/employee" element={<RoleLayout role="employee" />}>
                    <Route index element={<Navigate to="/employee/dashboard" replace />} />
                    <Route path="dashboard" element={<EmployeeDashboard />} />
                    <Route path="paths" element={<MyPaths />} />
                    <Route path="paths/:id" element={<PathView />} />
                    <Route path="paths/:id/modules/:moduleId" element={<ModuleView />} />
                    <Route path="documents" element={<EmployeeDocuments />} />
                    <Route path="profile" element={<Profile />} />
                  </Route>

                  {/* Đường dẫn cũ trước khi đổi tên vai trò */}
                  <Route path="/admin/*" element={<Navigate to="/hr/dashboard" replace />} />
                  <Route path="/manager/*" element={<Navigate to="/reviewer/dashboard" replace />} />
                  <Route index element={<Navigate to={auth.user ? HOME_PATH[auth.user.userRole] : "/login"} replace />} />
                  <Route path="*" element={<NotFound user={auth.user} />} />
                </Routes>
              </EnrollmentProvider>
            </PathsProvider>
        </DocumentsProvider>
      </AuthContext.Provider>
    </LanguageProvider>
  );
}
