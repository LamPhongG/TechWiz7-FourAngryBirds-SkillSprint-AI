import { useState } from "react";
import { CircleAlert } from "./Icons";
import { Button, Modal } from "./UI";
import { useLanguage } from "../contexts/LanguageContext";
import { useAuth } from "../hooks/useAuth";

const MIN_LENGTH = 8;
const EMPTY = { current: "", next: "", confirm: "" };

/** Change password for current logged-in user (all roles). `onDone` receives status message to show Toast. */
export default function ChangePasswordModal({ open, onClose, onDone }) {
  const { t } = useLanguage();
  const { changePassword } = useAuth();
  const [form, setForm] = useState(EMPTY);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  if (!open) return null;
  const set = (key, value) => setForm(f => ({ ...f, [key]: value }));
  const close = () => { setForm(EMPTY); setError(""); onClose(); };

  const submit = async (e) => {
    e.preventDefault();
    if (form.next.length < MIN_LENGTH) return setError(t("pwd_err_short", { n: MIN_LENGTH }));
    if (form.next !== form.confirm) return setError(t("pwd_err_mismatch"));
    if (form.next === form.current) return setError(t("err_password_unchanged"));
    setSaving(true);
    setError("");
    try {
      await changePassword(form.current, form.next);
      setForm(EMPTY);
      onClose();
      onDone?.(t("pwd_changed"));
    } catch (err) {
      setError(err.code ? t(err.code, err.vars) : err.status === 422 ? t("pwd_err_invalid") : t("err_network"));
    } finally {
      setSaving(false);
    }
  };

  const field = (key, label, autoComplete) => (
    <label>
      {label}
      <input id={`pwd-${key}`} type="password" autoComplete={autoComplete} value={form[key]}
        onChange={e => set(key, e.target.value)} />
    </label>
  );

  return (
    <Modal open title={t("pwd_change")} onClose={close} width="440px">
      <form onSubmit={submit} className="form-grid" style={{ gridTemplateColumns: "1fr" }}>
        {error && <div className="notice notice--danger"><CircleAlert size={16} /><span>{error}</span></div>}
        {field("current", t("pwd_current"), "current-password")}
        {field("next", t("pwd_new"), "new-password")}
        {field("confirm", t("pwd_confirm"), "new-password")}
        <small className="cell-sub">{t("pwd_hint", { n: MIN_LENGTH })}</small>
        <div className="modal-actions" style={{ marginTop: 4 }}>
          <Button variant="ghost" type="button" onClick={close}>{t("cancel")}</Button>
          <Button type="submit" disabled={saving}>{saving ? t("user_saving") : t("pwd_change")}</Button>
        </div>
      </form>
    </Modal>
  );
}
