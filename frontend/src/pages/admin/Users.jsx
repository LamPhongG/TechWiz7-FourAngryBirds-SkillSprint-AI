import { useState, useEffect, useMemo } from "react";
import {
  UserRound, Plus, Pencil, RefreshCw, Search, ShieldCheck,
  Check, X, CircleAlert, LockKeyhole, Unlock, Mail, Building2, BriefcaseBusiness, FileText
} from "../../components/Icons";
import { Card, SectionHeader, Button, Badge, Modal, Toast } from "../../components/UI";
import { useLanguage } from "../../contexts/LanguageContext";
import { useAuth } from "../../hooks/useAuth";
import { apiRequest } from "../../services/apiClient";
import { mapUser } from "../../services/apiMappers";
import { DEPARTMENTS, ROLES as JOB_ROLES } from "../../data/company";
import CreateEmployeeModal from "../../components/CreateEmployeeModal";

const SYSTEM_ROLES = [
  { key: "admin", label: "Admin", tone: "purple", color: "#8b5cf6" },
  { key: "hr", label: "HR", tone: "red", color: "#e11d48" },
  { key: "reviewer", label: "Reviewer", tone: "orange", color: "#d97706" },
  { key: "employee", label: "Employee", tone: "green", color: "#10b981" },
];

export default function AdminUsers() {
  const { t, tv } = useLanguage();
  const { user: currentUser } = useAuth();

  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [selectedRole, setSelectedRole] = useState("all");
  const [selectedStatus, setSelectedStatus] = useState("all");
  const [selectedDept, setSelectedDept] = useState("all");

  const [modalMode, setModalMode] = useState(null); // 'create' | 'cv' | 'edit' | 'delete' | 'restore' | null
  const [activeUser, setActiveUser] = useState(null);
  const [toastMessage, setToastMessage] = useState(null);
  const [formError, setFormError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  // Form fields
  const [formData, setFormData] = useState({
    name: "",
    email: "",
    password: "",
    user_role: "employee",
    department_code: "Company-wide",
    job_position_id: "",
    job_title: "",
  });

  const fetchUsers = async () => {
    try {
      setLoading(true);
      const data = await apiRequest("/users");
      setUsers((data || []).map(mapUser));
    } catch (err) {
      console.error("Failed to fetch users:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUsers();
  }, []);

  const openCreateModal = () => {
    setFormData({
      name: "",
      email: "",
      password: "",
      user_role: "employee",
      department_code: "Company-wide",
      job_position_id: "",
      job_title: "",
    });
    setFormError("");
    setModalMode("create");
  };

  const openEditModal = (u) => {
    setActiveUser(u);
    setFormData({
      name: u.name || "",
      email: u.email || "",
      password: "",
      user_role: u.userRole || "employee",
      department_code: u.department || "Company-wide",
      job_position_id: u.job_position_id || "",
      job_title: u.role || "",
    });
    setFormError("");
    setModalMode("edit");
  };

  const openDeleteModal = (u) => {
    setActiveUser(u);
    setModalMode("delete");
  };

  const openRestoreModal = (u) => {
    setActiveUser(u);
    setModalMode("restore");
  };

  const closeModal = () => {
    setModalMode(null);
    setActiveUser(null);
    setFormError("");
  };

  const handleCreateUser = async (e) => {
    e.preventDefault();
    setFormError("");
    if (!formData.name.trim() || !formData.email.trim() || !formData.password.trim()) {
      setFormError(t("user_err_required"));
      return;
    }
    if (formData.password.length < 6) {
      setFormError(t("user_err_password_short"));
      return;
    }

    try {
      setSubmitting(true);
      await apiRequest("/users", {
        method: "POST",
        body: {
          name: formData.name.trim(),
          email: formData.email.trim().toLowerCase(),
          password: formData.password,
          user_role: formData.user_role,
          department_code: formData.department_code || null,
          job_position_id: formData.job_position_id || null,
          job_title: formData.job_title ? formData.job_title.trim() : null,
        },
      });
      setToastMessage(t("user_save_success"));
      closeModal();
      await fetchUsers();
    } catch (err) {
      setFormError(err.message || t("user_err_create"));
    } finally {
      setSubmitting(false);
    }
  };

  const handleEditUser = async (e) => {
    e.preventDefault();
    if (!activeUser) return;
    setFormError("");
    if (!formData.name.trim()) {
      setFormError(t("user_err_name_required"));
      return;
    }

    try {
      setSubmitting(true);
      const payload = {
        name: formData.name.trim(),
        user_role: formData.user_role,
        department_code: formData.department_code || null,
        job_position_id: formData.job_position_id || null,
        job_title: formData.job_title ? formData.job_title.trim() : null,
      };
      if (formData.password.trim()) {
        if (formData.password.length < 6) {
          setFormError(t("user_err_password_short"));
          setSubmitting(false);
          return;
        }
        payload.password = formData.password.trim();
      }

      await apiRequest(`/users/${activeUser.id}`, {
        method: "PATCH",
        body: payload,
      });
      setToastMessage(t("user_save_success"));
      closeModal();
      await fetchUsers();
    } catch (err) {
      setFormError(err.message || t("user_err_update"));
    } finally {
      setSubmitting(false);
    }
  };

  const handleSoftDelete = async () => {
    if (!activeUser) return;
    try {
      setSubmitting(true);
      await apiRequest(`/users/${activeUser.id}`, { method: "DELETE" });
      setToastMessage(t("user_delete_success"));
      closeModal();
      await fetchUsers();
    } catch (err) {
      setFormError(err.message || t("user_err_deactivate"));
    } finally {
      setSubmitting(false);
    }
  };

  const handleRestore = async () => {
    if (!activeUser) return;
    try {
      setSubmitting(true);
      await apiRequest(`/users/${activeUser.id}/restore`, { method: "POST" });
      setToastMessage(t("user_restore_success"));
      closeModal();
      await fetchUsers();
    } catch (err) {
      setFormError(err.message || t("user_err_restore"));
    } finally {
      setSubmitting(false);
    }
  };

  const filteredUsers = useMemo(() => {
    return users.filter(u => {
      const q = search.trim().toLowerCase();
      const matchSearch = !q || (u.name && u.name.toLowerCase().includes(q)) || (u.email && u.email.toLowerCase().includes(q));
      const matchRole = selectedRole === "all" || u.userRole === selectedRole;
      const matchStatus = selectedStatus === "all" || (selectedStatus === "active" ? u.is_active : !u.is_active);
      const matchDept = selectedDept === "all" || u.department === selectedDept;
      return matchSearch && matchRole && matchStatus && matchDept;
    });
  }, [users, search, selectedRole, selectedStatus, selectedDept]);

  const availablePositions = useMemo(() => {
    if (!formData.department_code || formData.department_code === "Company-wide") {
      return JOB_ROLES;
    }
    return JOB_ROLES.filter(r => r.department === formData.department_code);
  }, [formData.department_code]);

  return (
    <div>
      <div className="page-heading">
        <div>
          <span className="eyebrow">{t("role_admin")}</span>
          <h1>{t("admin_users_title")}</h1>
          <p>{t("admin_users_desc")}</p>
        </div>
        <div className="heading-actions">
          <Button variant="secondary" onClick={() => setModalMode("cv")} icon={<FileText size={16} />}>
            {t("cv_create_button")}
          </Button>
          <Button onClick={openCreateModal} icon={<Plus size={16} />}>
            {t("user_add_new")}
          </Button>
        </div>
      </div>

      <Card style={{ marginBottom: "20px" }}>
        <div style={{ display: "flex", gap: "12px", flexWrap: "wrap", alignItems: "center", justifyContent: "space-between" }}>
          <div style={{ display: "flex", gap: "10px", flexWrap: "wrap", flex: 1, minWidth: "280px" }}>
            <div className="search-input" style={{ minWidth: "240px", flex: 1 }}>
              <Search size={16} />
              <input
                value={search}
                onChange={e => setSearch(e.target.value)}
                placeholder={t("user_search_placeholder")}
              />
            </div>

            <select
              className="filter-select"
              value={selectedRole}
              onChange={e => setSelectedRole(e.target.value)}
            >
              <option value="all">{t("user_filter_all_roles")}</option>
              {SYSTEM_ROLES.map(r => (
                <option key={r.key} value={r.key}>{t(`role_${r.key}`)}</option>
              ))}
            </select>

            <select
              className="filter-select"
              value={selectedStatus}
              onChange={e => setSelectedStatus(e.target.value)}
            >
              <option value="all">{t("user_filter_all_statuses")}</option>
              <option value="active">{t("user_status_active")}</option>
              <option value="inactive">{t("user_status_inactive")}</option>
            </select>

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
          </div>

          <div style={{ fontSize: "13px", color: "var(--muted)", fontWeight: 500 }}>
            {t("user_total_count", { n: filteredUsers.length })}
          </div>
        </div>
      </Card>

      <Card>
        {loading ? (
          <div style={{ padding: "40px", textAlign: "center", color: "var(--muted)" }}>
            {t("user_loading")}
          </div>
        ) : filteredUsers.length === 0 ? (
          <div style={{ padding: "40px", textAlign: "center", color: "var(--muted)" }}>
            {t("user_no_match")}
          </div>
        ) : (
          <div style={{ overflowX: "auto" }}>
            <table className="data-table" style={{ width: "100%", borderCollapse: "collapse" }}>
              <thead>
                <tr style={{ borderBottom: "1px solid var(--line)", textAlign: "left", fontSize: "13px", color: "var(--muted)" }}>
                  <th style={{ padding: "12px 14px" }}>{t("user_col_user")}</th>
                  <th style={{ padding: "12px 14px" }}>{t("user_col_role")}</th>
                  <th style={{ padding: "12px 14px" }}>{t("user_col_department")}</th>
                  <th style={{ padding: "12px 14px" }}>{t("user_col_status")}</th>
                  <th style={{ padding: "12px 14px", textAlign: "right" }}>{t("user_col_actions")}</th>
                </tr>
              </thead>
              <tbody>
                {filteredUsers.map(u => {
                  const roleCfg = SYSTEM_ROLES.find(r => r.key === u.userRole) || SYSTEM_ROLES[3];
                  const isCurrent = currentUser?.id === u.id;
                  return (
                    <tr
                      key={u.id}
                      style={{
                        borderBottom: "1px solid var(--line)",
                        opacity: u.is_active ? 1 : 0.65,
                        background: u.is_active ? "transparent" : "#fafafa",
                      }}
                    >
                      <td style={{ padding: "12px 14px" }}>
                        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                          <div
                            className="avatar"
                            style={{
                              width: "36px",
                              height: "36px",
                              borderRadius: "50%",
                              background: u.is_active ? `${roleCfg.color}18` : "#e2e8f0",
                              color: u.is_active ? roleCfg.color : "#64748b",
                              display: "grid",
                              placeItems: "center",
                              fontWeight: 700,
                              fontSize: "13px",
                            }}
                          >
                            {u.avatar || u.name?.slice(0, 2).toUpperCase()}
                          </div>
                          <div>
                            <div style={{ fontWeight: 600, fontSize: "14px", color: "var(--text)" }}>
                              {u.name} {isCurrent && <span style={{ fontSize: "11px", color: "var(--primary)", fontWeight: 700 }}>{t("user_you")}</span>}
                            </div>
                            <div style={{ fontSize: "12px", color: "var(--muted)" }}>{u.email}</div>
                          </div>
                        </div>
                      </td>
                      <td style={{ padding: "12px 14px" }}>
                        <span
                          style={{
                            display: "inline-flex",
                            alignItems: "center",
                            gap: "5px",
                            padding: "3px 8px",
                            borderRadius: "6px",
                            fontSize: "12px",
                            fontWeight: 600,
                            background: `${roleCfg.color}15`,
                            color: roleCfg.color,
                            border: `1px solid ${roleCfg.color}30`,
                          }}
                        >
                          <span style={{ width: "6px", height: "6px", borderRadius: "50%", background: roleCfg.color }} />
                          {t(`role_${u.userRole}`)}
                        </span>
                      </td>
                      <td style={{ padding: "12px 14px" }}>
                        <div style={{ fontSize: "13px", fontWeight: 500 }}>
                          {u.department ? tv(u.department) : "—"}
                        </div>
                        <div style={{ fontSize: "12px", color: "var(--muted)" }}>
                          {u.role || "—"}
                        </div>
                      </td>
                      <td style={{ padding: "12px 14px" }}>
                        {u.is_active ? (
                          <Badge tone="green">{t("user_status_active")}</Badge>
                        ) : (
                          <Badge tone="red">{t("user_status_inactive")}</Badge>
                        )}
                      </td>
                      <td style={{ padding: "12px 14px", textAlign: "right" }}>
                        <div className="row-actions" style={{ justifyContent: "flex-end" }}>
                          <Button
                            variant="ghost"
                            onClick={() => openEditModal(u)}
                            title={t("user_edit")}
                            style={{ padding: "6px 8px" }}
                          >
                            <Pencil size={15} />
                          </Button>

                          {u.is_active ? (
                            <Button
                              variant="ghost"
                              onClick={() => openDeleteModal(u)}
                              disabled={isCurrent}
                              title={isCurrent ? t("user_cannot_deactivate_self") : t("user_soft_delete")}
                              style={{ padding: "6px 8px", color: isCurrent ? "var(--muted)" : "var(--green)" }}
                            >
                              <Unlock size={15} />
                            </Button>
                          ) : (
                            <Button
                              variant="ghost"
                              onClick={() => openRestoreModal(u)}
                              title={t("user_restore")}
                              style={{ padding: "6px 8px", color: "var(--red)" }}
                            >
                              <LockKeyhole size={15} />
                            </Button>
                          )}
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

      {/* Add New User Modal */}
      <Modal
        open={modalMode === "create"}
        title={t("user_add_new")}
        onClose={closeModal}
        width="540px"
      >
        <form onSubmit={handleCreateUser} style={{ display: "grid", gap: "14px" }}>
          {formError && (
            <div className="notice notice--danger">
              <CircleAlert size={16} />
              <span>{formError}</span>
            </div>
          )}

          <div>
            <label style={{ display: "block", fontSize: "13px", fontWeight: 600, marginBottom: "6px" }}>
              {t("user_full_name")} *
            </label>
            <input
              className="cell-input"
              style={{ width: "100%", height: "38px" }}
              value={formData.name}
              onChange={e => setFormData({ ...formData, name: e.target.value })}
              placeholder={t("user_name_placeholder")}
            />
          </div>

          <div>
            <label style={{ display: "block", fontSize: "13px", fontWeight: 600, marginBottom: "6px" }}>
              {t("user_email")} *
            </label>
            <input
              type="email"
              className="cell-input"
              style={{ width: "100%", height: "38px" }}
              value={formData.email}
              onChange={e => setFormData({ ...formData, email: e.target.value })}
              placeholder="VD: an.nguyen@fourangrybirds.vn"
            />
          </div>

          <div>
            <label style={{ display: "block", fontSize: "13px", fontWeight: 600, marginBottom: "6px" }}>
              {t("user_password")} *
            </label>
            <input
              type="password"
              className="cell-input"
              style={{ width: "100%", height: "38px" }}
              value={formData.password}
              onChange={e => setFormData({ ...formData, password: e.target.value })}
              placeholder={t("user_password_placeholder")}
            />
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
            <div>
              <label style={{ display: "block", fontSize: "13px", fontWeight: 600, marginBottom: "6px" }}>
                {t("user_role")} *
              </label>
              <select
                className="filter-select"
                style={{ width: "100%", height: "38px" }}
                value={formData.user_role}
                onChange={e => setFormData({ ...formData, user_role: e.target.value })}
              >
                {SYSTEM_ROLES.map(r => (
                  <option key={r.key} value={r.key}>{t(`role_${r.key}`)}</option>
                ))}
              </select>
            </div>

            <div>
              <label style={{ display: "block", fontSize: "13px", fontWeight: 600, marginBottom: "6px" }}>
                {t("user_department")}
              </label>
              <select
                className="filter-select"
                style={{ width: "100%", height: "38px" }}
                value={formData.department_code}
                onChange={e => setFormData({ ...formData, department_code: e.target.value, job_position_id: "" })}
              >
                {DEPARTMENTS.map(d => (
                  <option key={d} value={d}>{tv(d)}</option>
                ))}
              </select>
            </div>
          </div>

          <div>
            <label style={{ display: "block", fontSize: "13px", fontWeight: 600, marginBottom: "6px" }}>
              {t("user_job_position")}
            </label>
            <select
              className="filter-select"
              style={{ width: "100%", height: "38px" }}
              value={formData.job_position_id}
              onChange={e => {
                const pos = JOB_ROLES.find(r => r.id === e.target.value);
                setFormData({
                  ...formData,
                  job_position_id: e.target.value,
                  job_title: pos ? pos.nameEn : formData.job_title,
                });
              }}
            >
              <option value="">{t("user_choose_position")}</option>
              {availablePositions.map(pos => (
                <option key={pos.id} value={pos.id}>{pos.nameEn} ({pos.name})</option>
              ))}
            </select>
          </div>

          <div style={{ display: "flex", justifyContent: "flex-end", gap: "10px", marginTop: "10px" }}>
            <Button variant="ghost" type="button" onClick={closeModal}>
              {t("cancel")}
            </Button>
            <Button type="submit" disabled={submitting}>
              {submitting ? t("user_processing") : t("user_add_new")}
            </Button>
          </div>
        </form>
      </Modal>

      {/* Edit User Modal */}
      <Modal
        open={modalMode === "edit"}
        title={t("user_edit")}
        onClose={closeModal}
        width="540px"
      >
        <form onSubmit={handleEditUser} style={{ display: "grid", gap: "14px" }}>
          {formError && (
            <div className="notice notice--danger">
              <CircleAlert size={16} />
              <span>{formError}</span>
            </div>
          )}

          <div>
            <label style={{ display: "block", fontSize: "13px", fontWeight: 600, marginBottom: "6px" }}>
              {t("user_email")}
            </label>
            <input
              className="cell-input"
              style={{ width: "100%", height: "38px", background: "#f8fafc", color: "var(--muted)" }}
              value={formData.email}
              disabled
            />
          </div>

          <div>
            <label style={{ display: "block", fontSize: "13px", fontWeight: 600, marginBottom: "6px" }}>
              {t("user_full_name")} *
            </label>
            <input
              className="cell-input"
              style={{ width: "100%", height: "38px" }}
              value={formData.name}
              onChange={e => setFormData({ ...formData, name: e.target.value })}
            />
          </div>

          <div>
            <label style={{ display: "block", fontSize: "13px", fontWeight: 600, marginBottom: "6px" }}>
              {t("user_password")} <small style={{ color: "var(--muted)" }}>({t("user_password_edit_hint")})</small>
            </label>
            <input
              type="password"
              className="cell-input"
              style={{ width: "100%", height: "38px" }}
              value={formData.password}
              onChange={e => setFormData({ ...formData, password: e.target.value })}
              placeholder={t("user_password_keep_placeholder")}
            />
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
            <div>
              <label style={{ display: "block", fontSize: "13px", fontWeight: 600, marginBottom: "6px" }}>
                {t("user_role")} *
              </label>
              <select
                className="filter-select"
                style={{ width: "100%", height: "38px" }}
                value={formData.user_role}
                onChange={e => setFormData({ ...formData, user_role: e.target.value })}
              >
                {SYSTEM_ROLES.map(r => (
                  <option key={r.key} value={r.key}>{t(`role_${r.key}`)}</option>
                ))}
              </select>
            </div>

            <div>
              <label style={{ display: "block", fontSize: "13px", fontWeight: 600, marginBottom: "6px" }}>
                {t("user_department")}
              </label>
              <select
                className="filter-select"
                style={{ width: "100%", height: "38px" }}
                value={formData.department_code}
                onChange={e => setFormData({ ...formData, department_code: e.target.value, job_position_id: "" })}
              >
                {DEPARTMENTS.map(d => (
                  <option key={d} value={d}>{tv(d)}</option>
                ))}
              </select>
            </div>
          </div>

          <div>
            <label style={{ display: "block", fontSize: "13px", fontWeight: 600, marginBottom: "6px" }}>
              {t("user_job_position")}
            </label>
            <select
              className="filter-select"
              style={{ width: "100%", height: "38px" }}
              value={formData.job_position_id}
              onChange={e => {
                const pos = JOB_ROLES.find(r => r.id === e.target.value);
                setFormData({
                  ...formData,
                  job_position_id: e.target.value,
                  job_title: pos ? pos.nameEn : formData.job_title,
                });
              }}
            >
              <option value="">{t("user_choose_position")}</option>
              {availablePositions.map(pos => (
                <option key={pos.id} value={pos.id}>{pos.nameEn} ({pos.name})</option>
              ))}
            </select>
          </div>

          <div style={{ display: "flex", justifyContent: "flex-end", gap: "10px", marginTop: "10px" }}>
            <Button variant="ghost" type="button" onClick={closeModal}>
              {t("cancel")}
            </Button>
            <Button type="submit" disabled={submitting}>
              {submitting ? t("user_saving") : t("save_changes")}
            </Button>
          </div>
        </form>
      </Modal>

      {/* Deactivate User Modal (Soft Delete) */}
      <Modal
        open={modalMode === "delete"}
        title={t("user_soft_delete_title")}
        onClose={closeModal}
        width="480px"
      >
        <div style={{ display: "grid", gap: "16px" }}>
          {formError && (
            <div className="notice notice--danger">
              <CircleAlert size={16} />
              <span>{formError}</span>
            </div>
          )}

          <div className="notice notice--warning" style={{ margin: 0 }}>
            <CircleAlert size={18} />
            <div>
              <strong>{t("user_soft_delete_heading")}</strong>
              <div style={{ marginTop: "4px", fontSize: "13px" }}>
                {t("user_soft_delete_confirm", { name: activeUser?.name, email: activeUser?.email })}
              </div>
            </div>
          </div>

          <p style={{ fontSize: "14px", color: "var(--muted)", margin: 0 }}>
            {t("user_soft_delete_note")}
          </p>

          <div style={{ display: "flex", justifyContent: "flex-end", gap: "10px" }}>
            <Button variant="ghost" onClick={closeModal}>
              {t("cancel")}
            </Button>
            <Button variant="danger" onClick={handleSoftDelete} disabled={submitting}>
              {submitting ? t("user_processing") : t("user_soft_delete")}
            </Button>
          </div>
        </div>
      </Modal>

      {/* Reactivate User Modal */}
      <Modal
        open={modalMode === "restore"}
        title={t("user_restore_title")}
        onClose={closeModal}
        width="480px"
      >
        <div style={{ display: "grid", gap: "16px" }}>
          {formError && (
            <div className="notice notice--danger">
              <CircleAlert size={16} />
              <span>{formError}</span>
            </div>
          )}

          <p style={{ fontSize: "14px", margin: 0 }}>
            {t("user_restore_confirm", { name: activeUser?.name, email: activeUser?.email })}
          </p>

          <div style={{ display: "flex", justifyContent: "flex-end", gap: "10px" }}>
            <Button variant="ghost" onClick={closeModal}>
              {t("cancel")}
            </Button>
            <Button onClick={handleRestore} disabled={submitting}>
              {submitting ? t("user_restoring") : t("user_restore")}
            </Button>
          </div>
        </div>
      </Modal>

      <CreateEmployeeModal open={modalMode === "cv"} onClose={closeModal} onCreated={fetchUsers} />

      <Toast message={toastMessage} onClose={() => setToastMessage(null)} />
    </div>
  );
}
