import { useState, createContext, useContext, useCallback, useEffect } from "react";
import { ROLES as JOB_ROLES } from "../data/company";
import { apiRequest, backendEnabled, setAuthToken, setUnauthorizedHandler } from "../services/apiClient";
import { mapUser } from "../services/apiMappers";

const AuthContext = createContext(null);

export const ROLES = {
  ADMIN: "admin",
  EMPLOYEE: "employee",
  REVIEWER: "reviewer",
  HR: "hr",
};

export const HOME_PATH = {
  [ROLES.ADMIN]: "/admin/dashboard",
  [ROLES.EMPLOYEE]: "/employee/dashboard",
  [ROLES.REVIEWER]: "/reviewer/dashboard",
  [ROLES.HR]: "/hr/dashboard",
};

const DEFAULT_EMPLOYEE_ROLE = "support-engineer";

function employeeUser(roleId) {
  const job = JOB_ROLES.find(r => r.id === roleId) || JOB_ROLES.find(r => r.id === DEFAULT_EMPLOYEE_ROLE);
  return {
    id: 1,
    name: "Alex Morgan",
    avatar: "AM",
    userRole: ROLES.EMPLOYEE,
    role_id: job.id,
    role: job.nameEn,
    department: job.department,
  };
}

const DEMO_USERS = {
  admin: { id: "USR-ADMIN-01", name: "Alexandre Admin", avatar: "AA", userRole: ROLES.ADMIN, role: "System Administrator", department: "Company-wide" },
  reviewer: { id: 6, name: "Sarah Chen", avatar: "SC", userRole: ROLES.REVIEWER, role: "Onboarding Reviewer", department: "Human Resources" },
  hr: { id: 7, name: "Jordan Lee", avatar: "JL", userRole: ROLES.HR, role: "HR Executive", department: "Human Resources" },
};

// Demo accounts: in browser mode, credentials checked client-side; in backend mode, backend verifies
// (bcrypt hashed passwords in DB). Hardcoded in source code for demonstration only.
export const DEMO_PASSWORD = "Demo@123";
export const DEMO_ACCOUNTS = [
  { email: "admin@fourangrybirds.vn", roleKey: ROLES.ADMIN, label: "Admin" },
  { email: "hr@fourangrybirds.vn", roleKey: ROLES.HR, label: "HR" },
  { email: "reviewer@fourangrybirds.vn", roleKey: ROLES.REVIEWER, label: "Reviewer" },
  { email: "sales.emp@fourangrybirds.vn", roleKey: ROLES.EMPLOYEE, roleId: "sales-exec", label: "Sales" },
  { email: "cs.emp@fourangrybirds.vn", roleKey: ROLES.EMPLOYEE, roleId: "cs-exec", label: "CS" },
  { email: "hr.emp@fourangrybirds.vn", roleKey: ROLES.EMPLOYEE, roleId: "hr-exec", label: "HR Staff" },
  { email: "finance.emp@fourangrybirds.vn", roleKey: ROLES.EMPLOYEE, roleId: "finance-associate", label: "Finance" },
  { email: "ops.emp@fourangrybirds.vn", roleKey: ROLES.EMPLOYEE, roleId: "ops-coordinator", label: "Ops" },
  { email: "marketing.emp@fourangrybirds.vn", roleKey: ROLES.EMPLOYEE, roleId: "marketing-exec", label: "Marketing" },
  { email: "alex.morgan@fourangrybirds.vn", roleKey: ROLES.EMPLOYEE, roleId: "support-engineer", label: "Support Eng" },
  { email: "branch.mgr@fourangrybirds.vn", roleKey: ROLES.EMPLOYEE, roleId: "branch-manager", label: "Branch Mgr" },
  { email: "data.analyst@fourangrybirds.vn", roleKey: ROLES.EMPLOYEE, roleId: "data-analyst", label: "Data Analyst" },
  { email: "team.lead@fourangrybirds.vn", roleKey: ROLES.EMPLOYEE, roleId: "team-leader", label: "Tech Lead" },
];

// Do not remember: session in sessionStorage, cleared upon tab close. Remember: localStorage, persists across browser restarts.
// Session is always maintained across reloads so audit log tracks the actor.
const SESSION_KEY = "skillsprint.session.v2";

function build(session) {
  if (!session || typeof session !== "object") return null;
  // Backend mode: user profile returned by API upon login
  if (session.token) return session.user && typeof session.user === "object" ? session.user : null;
  if (session.roleKey === ROLES.EMPLOYEE) return employeeUser(session.roleId);
  return DEMO_USERS[session.roleKey] || null;
}

function readSession() {
  for (const storage of [() => sessionStorage, () => localStorage]) {
    try {
      const value = JSON.parse(storage().getItem(SESSION_KEY));
      // Sessions from different modes (with/without backend) are incompatible with current mode
      if (value && !!value.token === backendEnabled()) return value;
    } catch {
      // Storage blocked or corrupted — attempt alternative storage
    }
  }
  return null;
}

function writeSession(session) {
  try {
    sessionStorage.removeItem(SESSION_KEY);
    localStorage.removeItem(SESSION_KEY);
    if (session) (session.remember ? localStorage : sessionStorage).setItem(SESSION_KEY, JSON.stringify(session));
  } catch {
    // Storage blocked — session persists in memory only
  }
}

export function useAuthProvider() {
  const [session, setSession] = useState(() => {
    const stored = readSession();
    // Set token immediately on initialization so child providers can make API calls on first render
    setAuthToken(stored?.token);
    return stored;
  });
  const user = build(session);

  const persist = useCallback((next) => {
    setAuthToken(next?.token);
    setSession(next);
    writeSession(next);
  }, []);

  useEffect(() => {
    setUnauthorizedHandler(() => persist(null));
    return () => setUnauthorizedHandler(null);
  }, [persist]);

  /**
   * @returns {string|null|Promise<string|null>} role when email + password match, null when invalid.
   *   Returns Promise in backend mode; network errors are thrown so page reports the exact cause.
   */
  const login = (email, password, { remember = false } = {}) => {
    if (backendEnabled()) {
      return apiRequest("/auth/login", { method: "POST", body: { email: String(email).trim(), password } })
        .then(res => {
          const profile = mapUser(res.user);
          persist({ token: res.access_token, user: profile, remember });
          return profile.userRole;
        })
        .catch(e => {
          if (e.status === 401 || e.status === 422) return null;
          throw e;
        });
    }
    const account = DEMO_ACCOUNTS.find(a => a.email === String(email).trim().toLowerCase());
    if (!account || password !== DEMO_PASSWORD) return null;
    persist({ roleKey: account.roleKey, roleId: DEFAULT_EMPLOYEE_ROLE, remember });
    return account.roleKey;
  };

  const logout = () => persist(null);

  // Browser demo only: in backend mode, job position is real DB data and not modified here
  const setEmployeePosition = (roleId) => {
    if (!backendEnabled() && session?.roleKey === ROLES.EMPLOYEE) persist({ ...session, roleId });
  };

  // Change password for logged-in user (backend mode only). Errors are thrown for modal display.
  const changePassword = (currentPassword, newPassword) =>
    apiRequest("/auth/change-password", {
      method: "POST", body: { current_password: currentPassword, new_password: newPassword },
    }).then(res => {
      if (session?.token) persist({ ...session, user: mapUser(res) });
      return mapUser(res);
    });

  return { user, login, logout, setEmployeePosition, changePassword };
}

export function useAuth() {
  return useContext(AuthContext);
}

export { AuthContext };
