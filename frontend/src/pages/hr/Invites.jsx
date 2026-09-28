import { useCallback, useEffect, useState } from "react";
import { CircleAlert, Plus } from "../../components/Icons";
import { Badge, Button, Card, EmptyState, SectionHeader } from "../../components/UI";
import CreateEmployeeModal from "../../components/CreateEmployeeModal";
import { apiRequest, backendEnabled } from "../../services/apiClient";
import { mapUser } from "../../services/apiMappers";
import { useLanguage } from "../../contexts/LanguageContext";
import { DEPARTMENTS as DEPT_CODES } from "../../data/company";

/**
 * HR creates employee accounts directly: system generates a temporary password and delivers it
 * via email, allowing immediate employee login. The list below shows recently created employee accounts.
 */
export default function HrInvites() {
  const { t, tv } = useLanguage();
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(backendEnabled());
  const [loadError, setLoadError] = useState("");
  const [modalOpen, setModalOpen] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setLoadError("");
    try {
      const rows = await apiRequest("/users?role=employee");
      setUsers(rows.map(mapUser));
    } catch (err) {
      setLoadError(err.code || "err_network");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (backendEnabled()) load();
  }, [load]);

  if (!backendEnabled()) {
    return (
      <Card>
        <EmptyState title={t("invites_title")} description={t("invites_needs_backend")} />
      </Card>
    );
  }

  const deptName = code => tv(DEPT_CODES.includes(code) ? code : code || "");
  const recent = users.slice(0, 20);

  return (
    <div>
      <div className="page-heading">
        <div>
          <span className="eyebrow">HR</span>
          <h1>{t("invites_title")}</h1>
          <p>{t("invites_subtitle")}</p>
        </div>
        <div className="heading-actions">
          <Button onClick={() => setModalOpen(true)} icon={<Plus size={16} />}>{t("invites_new")}</Button>
        </div>
      </div>

      <Card>
        <SectionHeader title={t("invites_list")} subtitle={t("invites_list_hint")} />
        {loading && <p className="cell-sub">{t("invites_loading")}</p>}
        {!loading && loadError && (
          <div className="notice notice--danger"><CircleAlert size={16} /><span>{t(loadError)}</span></div>
        )}
        {!loading && !loadError && recent.length === 0 && (
          <EmptyState title={t("invites_empty")} description={t("invites_empty_hint")}
            action={<Button onClick={() => setModalOpen(true)} icon={<Plus size={16} />}>{t("invites_new")}</Button>} />
        )}
        {!loading && recent.length > 0 && (
          <ul className="invite-list">
            {recent.map(u => (
              <li key={u.id} className="invite-item">
                <div className="invite-item__info">
                  <div className="invite-item__top">
                    <Badge tone={u.is_active ? "green" : "default"}>{t(u.is_active ? "user_status_active" : "user_status_inactive")}</Badge>
                    <strong>{u.name}</strong>
                    <span className="cell-sub">{u.role}{u.department ? ` · ${deptName(u.department)}` : ""}</span>
                  </div>
                  <div className="invite-item__line">{u.email}</div>
                </div>
              </li>
            ))}
          </ul>
        )}
      </Card>

      <CreateEmployeeModal open={modalOpen} onClose={() => setModalOpen(false)} onCreated={load} />
    </div>
  );
}
