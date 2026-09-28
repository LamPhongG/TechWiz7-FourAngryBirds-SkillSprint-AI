import { useMemo, useRef, useState } from "react";
import { CircleAlert, CircleCheck, Copy, Loader2, Upload } from "./Icons";
import { Button, Modal } from "./UI";
import { useLanguage } from "../contexts/LanguageContext";
import { apiRequest } from "../services/apiClient";
import { mapUser } from "../services/apiMappers";
import { DEPARTMENTS, ROLES as JOB_ROLES } from "../data/company";

const CV_ACCEPT = ".pdf,.docx,.txt,.md";
const LEVELS = ["Beginner", "Intermediate", "Advanced"];
const EMPTY_FORM = {
  name: "", email: "", department: "", job_position_id: "", experience_level: "", competencies: "", previous_experience: "",
};

/**
 * Create employee account: from CV (backend parses CV using Python without persisting file or extracting phone/address/DOB)
 * or direct manual input. HR/Admin reviews and edits information; backend generates password and emails credentials
 * to the employee — employee does not self-register, but simply logs in with credentials received.
 */
export default function CreateEmployeeModal({ open, onClose, onCreated }) {
  const { t, tv } = useLanguage();
  const fileInput = useRef(null);
  const [step, setStep] = useState("upload"); // upload | form | done
  const [fileName, setFileName] = useState("");
  const [warnings, setWarnings] = useState([]);
  const [form, setForm] = useState(EMPTY_FORM);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [copied, setCopied] = useState(false);

  const positions = useMemo(
    () => JOB_ROLES.filter(r => !form.department || r.department === form.department),
    [form.department],
  );

  if (!open) return null;
  const set = (key, value) => setForm(f => ({ ...f, [key]: value }));
  const errorText = err => (err.code ? t(err.code, err.vars) : err.message || t("err_network"));

  const reset = () => {
    setStep("upload"); setFileName(""); setWarnings([]); setForm(EMPTY_FORM);
    setResult(null); setError(""); setBusy(false); setCopied(false);
  };
  const close = () => { reset(); onClose(); };
  const skipToForm = () => { setFileName(""); setWarnings([]); setForm(EMPTY_FORM); setStep("form"); };

  const readCv = async (file) => {
    if (!file) return;
    setFileName(file.name);
    setError("");
    setBusy(true);
    try {
      const body = new FormData();
      body.append("file", file);
      const draft = await apiRequest("/users/cv/parse", { method: "POST", body });
      setForm({
        ...EMPTY_FORM,
        name: draft.name || "",
        email: draft.email || "",
        experience_level: draft.experience_level || "",
        competencies: (draft.competencies || []).join(", "),
        previous_experience: draft.previous_experience || "",
      });
      setWarnings(draft.warnings || []);
      setStep("form");
    } catch (err) {
      setError(errorText(err));
    } finally {
      setBusy(false);
      if (fileInput.current) fileInput.current.value = "";
    }
  };

  const create = async (e) => {
    e.preventDefault();
    if (!form.name.trim() || !form.email.trim() || !form.job_position_id) {
      setError(t("cv_err_required"));
      return;
    }
    setError("");
    setBusy(true);
    try {
      const res = await apiRequest("/users/from-cv", {
        method: "POST",
        body: {
          name: form.name.trim(),
          email: form.email.trim().toLowerCase(),
          job_position_id: form.job_position_id,
          experience_level: form.experience_level || null,
          previous_experience: form.previous_experience.trim() || null,
          competencies: form.competencies.split(",").map(s => s.trim()).filter(Boolean).slice(0, 20),
        },
      });
      setResult({ ...res, user: mapUser(res.user) });
      setStep("done");
      onCreated?.();
    } catch (err) {
      setError(errorText(err));
    } finally {
      setBusy(false);
    }
  };

  const copyPassword = async () => {
    try {
      await navigator.clipboard.writeText(result.temporary_password);
      setCopied(true);
    } catch {
      setCopied(false);
    }
  };

  const errorBox = error && <div className="notice notice--danger"><CircleAlert size={16} /><span>{error}</span></div>;

  return (
    <Modal open title={t("cv_create_title")} onClose={close} width="620px">
      {step === "upload" && (
        <div className="cv-modal">
          {errorBox}
          <div className="upload-zone">
            {busy ? <Loader2 size={28} className="spin" /> : <Upload size={28} />}
            <h3>{busy ? t("cv_reading", { name: fileName }) : t("cv_upload_title")}</h3>
            <p>{t("cv_upload_desc")}</p>
            <input ref={fileInput} id="cv-file" type="file" accept={CV_ACCEPT} hidden
              onChange={e => readCv(e.target.files?.[0])} />
            <Button type="button" disabled={busy} onClick={() => fileInput.current?.click()}>{t("cv_choose_file")}</Button>
          </div>
          <div className="modal-actions" style={{ marginTop: 0, justifyContent: "center" }}>
            <Button variant="ghost" type="button" disabled={busy} onClick={skipToForm}>{t("cv_skip_manual")}</Button>
          </div>
          <small className="cell-sub">{t("cv_privacy_note")}</small>
        </div>
      )}

      {step === "form" && (
        <form onSubmit={create} className="cv-modal">
          {errorBox}
          {fileName && (
            <div className="notice notice--info">
              <CircleCheck size={16} />
              <span>{t("cv_read_from", { name: fileName })}</span>
            </div>
          )}
          {warnings.length > 0 && (
            <div className="notice notice--warning">
              <CircleAlert size={16} />
              <span>{warnings.map(w => t(w)).join(" · ")}</span>
            </div>
          )}
          <div className="form-grid cv-form">
            <label>{t("user_full_name")} *
              <input id="cv-name" value={form.name} onChange={e => set("name", e.target.value)} />
            </label>
            <label>{t("user_email")} *
              <input id="cv-email" type="email" value={form.email} onChange={e => set("email", e.target.value)} />
            </label>
            <label>{t("user_department")}
              <select id="cv-department" value={form.department}
                onChange={e => setForm(f => ({ ...f, department: e.target.value, job_position_id: "" }))}>
                <option value="">{t("filter_department_all")}</option>
                {DEPARTMENTS.filter(d => d !== "Company-wide").map(d => <option key={d} value={d}>{tv(d)}</option>)}
              </select>
            </label>
            <label>{t("user_job_position")} *
              <select id="cv-position" value={form.job_position_id}
                onChange={e => {
                  const pos = JOB_ROLES.find(r => r.id === e.target.value);
                  setForm(f => ({ ...f, job_position_id: e.target.value, department: pos ? pos.department : f.department }));
                }}>
                <option value="">{t("user_choose_position")}</option>
                {positions.map(pos => <option key={pos.id} value={pos.id}>{pos.nameEn} ({pos.name})</option>)}
              </select>
            </label>
            <label>{t("cv_experience_level")}
              <select id="cv-level" value={form.experience_level} onChange={e => set("experience_level", e.target.value)}>
                <option value="">{t("cv_level_unknown")}</option>
                {LEVELS.map(l => <option key={l} value={l}>{tv(l)}</option>)}
              </select>
            </label>
            <label>{t("cv_competencies")}
              <input id="cv-skills" value={form.competencies} onChange={e => set("competencies", e.target.value)}
                placeholder={t("cv_competencies_hint")} />
            </label>
            <label style={{ gridColumn: "1 / -1" }}>{t("cv_previous_experience")}
              <textarea id="cv-experience" value={form.previous_experience} maxLength={2000}
                onChange={e => set("previous_experience", e.target.value)} />
            </label>
          </div>
          <small className="cell-sub">{t("cv_password_note")}</small>
          <div className="modal-actions" style={{ marginTop: 0 }}>
            <Button variant="ghost" type="button" onClick={reset}>{t("cv_choose_other")}</Button>
            <Button type="submit" disabled={busy}>{busy ? t("user_processing") : t("cv_create_submit")}</Button>
          </div>
        </form>
      )}

      {step === "done" && result && (
        <div className="cv-modal">
          {result.email_sent ? (
            <div className="notice notice--info" data-testid="cv-email-sent">
              <CircleCheck size={16} />
              <span>{t("cv_done_email_sent", { name: result.user.name, email: result.user.email })}</span>
            </div>
          ) : (
            <>
              <div className="notice notice--warning" data-testid="cv-email-failed">
                <CircleAlert size={16} />
                <span>{t("cv_done_email_failed", { email: result.user.email })}</span>
              </div>
              <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
                <code id="cv-temp-password" style={{ fontSize: 17, padding: "8px 12px", background: "var(--bg)", borderRadius: 8, letterSpacing: 1 }}>
                  {result.temporary_password}
                </code>
                <Button variant="ghost" type="button" icon={<Copy size={15} />} onClick={copyPassword}>
                  {copied ? t("cv_copied") : t("cv_copy")}
                </Button>
              </div>
              <small className="cell-sub">{t("cv_password_once")}</small>
            </>
          )}
          <div className="modal-actions" style={{ marginTop: 0 }}>
            <Button variant="ghost" type="button" onClick={reset}>{t("cv_create_another")}</Button>
            <Button type="button" onClick={close}>{t("cv_close")}</Button>
          </div>
        </div>
      )}
    </Modal>
  );
}
