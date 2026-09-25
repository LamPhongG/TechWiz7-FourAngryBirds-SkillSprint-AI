import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Send, RefreshCw, Trash2, CircleCheck, CircleAlert, MessageSquare, Archive, Loader2 } from "../Icons";
import { Button, Modal } from "../UI";
import { FinalStatusBadge } from "./Badges";
import { ReasonField } from "./ReasonField";
import { useLanguage } from "../../contexts/LanguageContext";
import { usePaths, PathError } from "../../contexts/PathsContext";
import { useDocuments } from "../../contexts/DocumentsContext";
import { DEPARTMENTS, ROLES as JOB_ROLES } from "../../data/company";
import { approvalRule, can } from "../../utils/pathWorkflow";
import { formatDateTime } from "../../utils/helpers";

/** Thanh thao tác theo vai trò và trạng thái lộ trình */
export default function PathActions({ path, checks, role, basePath }) {
  const { t, tv, pick, locale } = useLanguage();
  const [modal, setModal] = useState(null);

  const buttons = [];
  if (can(role, "submit", path)) buttons.push(<Button key="submit" onClick={() => setModal("submit")} icon={<Send size={15} />}>{t(path.status === "changes_requested" ? "action_resubmit" : "action_submit")}</Button>);
  if (can(role, "regenerate", path)) buttons.push(<Button key="regen" variant="secondary" onClick={() => setModal("regenerate")} icon={<RefreshCw size={15} />}>{t("action_regenerate")}</Button>);
  if (can(role, "delete", path)) buttons.push(<Button key="delete" variant="secondary" className="btn btn-danger-outline" onClick={() => setModal("delete")} icon={<Trash2 size={15} />}>{t("action_delete_draft")}</Button>);
  if (can(role, "request_changes", path)) buttons.push(<Button key="changes" variant="secondary" className="btn btn-danger-outline" onClick={() => setModal("request_changes")} icon={<MessageSquare size={15} />}>{t("action_request_changes")}</Button>);
  if (can(role, "approve", path)) buttons.push(<Button key="approve" onClick={() => setModal("approve")} icon={<CircleCheck size={15} />}>{t("action_approve_publish")}</Button>);
  if (can(role, "archive", path)) buttons.push(<Button key="archive" variant="secondary" onClick={() => setModal("archive")} icon={<Archive size={15} />}>{t("action_archive")}</Button>);

  return (
    <div className="path-actions">
      {path.status === "published" && path.approval && (
        <div className="decision-banner decision-banner--approve">
          <CircleCheck size={15} />
          <span>{t("published_by", { name: path.approval.by?.name, date: formatDateTime(path.approval.at, locale) })}</span>
          <FinalStatusBadge status={path.approval.final_status} />
          <span className="cell-sub">
            {t("published_to_label")}: {[...path.published_to.departments.map(d => tv(d)), ...path.published_to.roles.map(r => pick(JOB_ROLES.find(x => x.id === r), "name"))].join(", ")}
          </span>
          {path.approval.reason && <em>“{path.approval.reason}”</em>}
        </div>
      )}
      {buttons.length > 0 && <div className="review-actions" style={{ marginTop: 0 }}>{buttons}</div>}

      {modal === "submit" && <SubmitModal path={path} checks={checks} onClose={() => setModal(null)} />}
      {modal === "regenerate" && <RegenerateModal path={path} onClose={() => setModal(null)} />}
      {modal === "delete" && <DeleteModal path={path} basePath={basePath} onClose={() => setModal(null)} />}
      {modal === "request_changes" && <RequestChangesModal path={path} checks={checks} onClose={() => setModal(null)} />}
      {modal === "approve" && <ApproveModal path={path} checks={checks} onClose={() => setModal(null)} />}
      {modal === "archive" && <ArchiveModal path={path} onClose={() => setModal(null)} />}
    </div>
  );
}

function useRunner() {
  const { t } = useLanguage();
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const run = async (fn, onDone) => {
    setError("");
    setBusy(true);
    try {
      await fn();
      onDone?.();
    } catch (e) {
      setError(e instanceof PathError ? t(e.key, e.vars) : e.message === "NO_CONTENT" ? t("err_no_content") : e.message);
    } finally {
      setBusy(false);
    }
  };
  const errorBox = error && <div className="notice notice--danger"><CircleAlert size={16} /><span>{error}</span></div>;
  return { run, busy, errorBox };
}

function SubmitModal({ path, checks, onClose }) {
  const { t } = useLanguage();
  const { submitPath } = usePaths();
  const { run, busy, errorBox } = useRunner();
  const [note, setNote] = useState("");
  const openComments = path.comments.filter(c => !c.reply_to && !c.resolved).length;
  return (
    <Modal open title={t(path.status === "changes_requested" ? "action_resubmit" : "action_submit")} onClose={onClose}>
      <div className="decision-current"><span>{t("current_check_status")}</span><FinalStatusBadge status={checks.final_status} /></div>
      {openComments > 0 && <div className="notice notice--warning"><CircleAlert size={16} /><span>{t("submit_open_comments", { n: openComments })}</span></div>}
      <ReasonField value={note} onChange={setNote} label={t("submit_note_label")} />
      {errorBox}
      <div className="modal-actions">
        <Button variant="secondary" onClick={onClose}>{t("cancel")}</Button>
        <Button disabled={busy} onClick={() => run(() => submitPath(path.id, { note, finalStatus: checks.final_status }), onClose)} icon={<Send size={15} />}>{t("action_submit")}</Button>
      </div>
    </Modal>
  );
}

function RegenerateModal({ path, onClose }) {
  const { t } = useLanguage();
  const { regeneratePath } = usePaths();
  const { activeDocuments, processed } = useDocuments();
  const { run, busy, errorBox } = useRunner();
  const codes = new Set(path.sources.map(s => s.code));
  // Dùng phiên bản đang hiệu lực của cùng mã tài liệu — tài liệu mới cập nhật sẽ được lấy vào
  const docs = activeDocuments.filter(d => codes.has(d.code) && processed[d.id]);
  const role = JOB_ROLES.find(r => r.id === path.target.role_id);
  return (
    <Modal open title={t("action_regenerate")} onClose={onClose}>
      <p>{t("regenerate_desc", { n: docs.length })}</p>
      {path.status === "changes_requested" && <p className="cell-sub">{t("regenerate_keep_comments")}</p>}
      {errorBox}
      <div className="modal-actions">
        <Button variant="secondary" onClick={onClose}>{t("cancel")}</Button>
        <Button disabled={busy || docs.length === 0} icon={busy ? <Loader2 size={15} className="spin" /> : <RefreshCw size={15} />}
          onClick={() => run(() => regeneratePath(path.id, { role, sourceDocs: docs, processed }), onClose)}>
          {t("action_regenerate")}
        </Button>
      </div>
    </Modal>
  );
}

function DeleteModal({ path, basePath, onClose }) {
  const { t } = useLanguage();
  const { deletePath } = usePaths();
  const navigate = useNavigate();
  const { run, errorBox } = useRunner();
  return (
    <Modal open title={t("action_delete_draft")} onClose={onClose}>
      <p>{t("delete_draft_confirm")}</p>
      {errorBox}
      <div className="modal-actions">
        <Button variant="secondary" onClick={onClose}>{t("cancel")}</Button>
        <Button className="btn btn-danger" onClick={() => run(() => deletePath(path.id), () => navigate(basePath))}>{t("action_delete")}</Button>
      </div>
    </Modal>
  );
}

function RequestChangesModal({ path, checks, onClose }) {
  const { t } = useLanguage();
  const { requestChanges } = usePaths();
  const { run, busy, errorBox } = useRunner();
  const [message, setMessage] = useState("");
  return (
    <Modal open title={t("action_request_changes")} onClose={onClose}>
      <p className="cell-sub">{t("request_changes_desc")}</p>
      <ReasonField value={message} onChange={setMessage} required label={t("request_changes_label")} />
      {errorBox}
      <div className="modal-actions">
        <Button variant="secondary" onClick={onClose}>{t("cancel")}</Button>
        <Button className="btn btn-danger" disabled={busy} onClick={() => run(() => requestChanges(path.id, { message, finalStatus: checks.final_status }), onClose)}>{t("action_request_changes")}</Button>
      </div>
    </Modal>
  );
}

function ApproveModal({ path, checks, onClose }) {
  const { t, tv, pick } = useLanguage();
  const { approvePath } = usePaths();
  const { run, busy, errorBox } = useRunner();
  const rule = approvalRule(checks);
  const [departments, setDepartments] = useState([path.target.department]);
  const [roles, setRoles] = useState([path.target.role_id]);
  const [reason, setReason] = useState("");
  const toggle = (list, setList, v) => setList(list.includes(v) ? list.filter(x => x !== v) : [...list, v]);

  return (
    <Modal open title={t("action_approve_publish")} onClose={onClose} width="720px">
      <div className="decision-current"><span>{t("current_check_status")}</span><FinalStatusBadge status={checks.final_status} /></div>
      {!rule.allowed ? (
        <div className="notice notice--danger"><CircleAlert size={16} /><span>{t("approve_blocked_desc")}</span></div>
      ) : (
        <>
          <p className="cell-sub">{t("publish_desc")}</p>
          <div className="field-label">{t("publish_departments")}</div>
          <div className="check-grid">
            {DEPARTMENTS.map(d => (
              <label key={d} className="checkbox"><input type="checkbox" checked={departments.includes(d)} onChange={() => toggle(departments, setDepartments, d)} /> {tv(d)}</label>
            ))}
          </div>
          <div className="field-label" style={{ marginTop: 12 }}>{t("publish_roles")}</div>
          <div className="check-grid">
            {JOB_ROLES.map(r => (
              <label key={r.id} className="checkbox"><input type="checkbox" checked={roles.includes(r.id)} onChange={() => toggle(roles, setRoles, r.id)} /> {pick(r, "name")}</label>
            ))}
          </div>
          <div style={{ marginTop: 12 }}>
            <ReasonField value={reason} onChange={setReason} required={rule.reasonRequired} label={t(rule.reasonRequired ? "approve_reason_required" : "reason_label_optional")} />
          </div>
        </>
      )}
      {errorBox}
      <div className="modal-actions">
        <Button variant="secondary" onClick={onClose}>{t("cancel")}</Button>
        {rule.allowed && (
          <Button disabled={busy} onClick={() => run(() => approvePath(path.id, { departments, roles, reason, checks }), onClose)} icon={<CircleCheck size={15} />}>
            {t("action_approve_publish")}
          </Button>
        )}
      </div>
    </Modal>
  );
}

function ArchiveModal({ path, onClose }) {
  const { t } = useLanguage();
  const { archivePath } = usePaths();
  const { run, busy, errorBox } = useRunner();
  const [reason, setReason] = useState("");
  return (
    <Modal open title={t("action_archive")} onClose={onClose}>
      <p className="cell-sub">{t("archive_desc")}</p>
      <ReasonField value={reason} onChange={setReason} required />
      {errorBox}
      <div className="modal-actions">
        <Button variant="secondary" onClick={onClose}>{t("cancel")}</Button>
        <Button className="btn btn-danger" disabled={busy} onClick={() => run(() => archivePath(path.id, reason), onClose)}>{t("action_archive")}</Button>
      </div>
    </Modal>
  );
}
