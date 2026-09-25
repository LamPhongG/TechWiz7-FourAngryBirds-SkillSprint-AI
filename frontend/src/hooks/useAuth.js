import { useState, createContext, useContext, useCallback } from "react";
import { ROLES as JOB_ROLES } from "../data/company";

const AuthContext = createContext(null);

export const ROLES = {
  EMPLOYEE: "employee",
  REVIEWER: "reviewer",
  HR: "hr",
};

export const HOME_PATH = {
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
  reviewer: { id: 6, name: "Sarah Chen", avatar: "SC", userRole: ROLES.REVIEWER, role: "Onboarding Reviewer", department: "Human Resources" },
  hr: { id: 7, name: "Jordan Lee", avatar: "JL", userRole: ROLES.HR, role: "HR Executive", department: "Human Resources" },
};

// Tài khoản demo cho tới khi backend có xác thực thật. Mật khẩu nằm trong mã nguồn nên chỉ dùng để trình diễn.
export const DEMO_PASSWORD = "Demo@123";
export const DEMO_ACCOUNTS = [
  { email: "hr@fourangrybirds.vn", roleKey: ROLES.HR },
  { email: "reviewer@fourangrybirds.vn", roleKey: ROLES.REVIEWER },
  { email: "alex.morgan@fourangrybirds.vn", roleKey: ROLES.EMPLOYEE },
];

// Không ghi nhớ: phiên ở sessionStorage, đóng tab là hết. Ghi nhớ: ở localStorage, còn sau khi đóng trình duyệt.
// Phiên luôn được giữ qua lần tải lại trang để audit log biết ai thao tác.
const SESSION_KEY = "skillsprint.session.v2";

function build(session) {
  if (!session || typeof session !== "object") return null;
  if (session.roleKey === ROLES.EMPLOYEE) return employeeUser(session.roleId);
  return DEMO_USERS[session.roleKey] || null;
}

function readSession() {
  for (const storage of [() => sessionStorage, () => localStorage]) {
    try {
      const value = JSON.parse(storage().getItem(SESSION_KEY));
      if (value) return value;
    } catch {
      // Storage bị chặn hoặc dữ liệu hỏng — thử nơi lưu còn lại
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
    // Storage bị chặn — phiên chỉ sống trong bộ nhớ
  }
}

export function useAuthProvider() {
  const [session, setSession] = useState(readSession);
  const user = build(session);

  const persist = useCallback((next) => {
    setSession(next);
    writeSession(next);
  }, []);

  /** @returns {string|null} vai trò khi đúng email + mật khẩu, null khi sai */
  const login = (email, password, { remember = false } = {}) => {
    const account = DEMO_ACCOUNTS.find(a => a.email === String(email).trim().toLowerCase());
    if (!account || password !== DEMO_PASSWORD) return null;
    persist({ roleKey: account.roleKey, roleId: DEFAULT_EMPLOYEE_ROLE, remember });
    return account.roleKey;
  };

  const logout = () => persist(null);

  // Chỉ dùng cho demo: đổi vị trí của nhân viên để xem lộ trình của phòng ban khác
  const setEmployeePosition = (roleId) => {
    if (session?.roleKey === ROLES.EMPLOYEE) persist({ ...session, roleId });
  };

  return { user, login, logout, setEmployeePosition };
}

export function useAuth() {
  return useContext(AuthContext);
}

export { AuthContext };
