import { useState } from "react";
import { Send, X, CircleCheck, CircleAlert } from "../Icons";
import { Badge, Button } from "../UI";
import { useLanguage } from "../../contexts/LanguageContext";
import { usePaths, PathError } from "../../contexts/PathsContext";
import { formatDateTime } from "../../utils/helpers";

/**
 * Trao đổi giữa Reviewer và HR trên một lộ trình. Góp ý có thể gắn vào một mục cụ thể
 * (học phần, bài học, câu hỏi…); HR đánh dấu đã xử lý trước khi gửi duyệt lại.
 */
export default function PathComments({ path, canComment, itemRef, onClearItemRef }) {
  const { t, locale } = useLanguage();
  const { addComment, resolveComment } = usePaths();
  const [text, setText] = useState("");
  const [replyTo, setReplyTo] = useState(null);
  const [error, setError] = useState("");

  const run = (fn) => {
    setError("");
    try { fn(); return true; } catch (e) { setError(e instanceof PathError ? t(e.key, e.vars) : e.message); return false; }
  };

  const send = () => {
    if (run(() => addComment(path.id, { text, itemRef, replyTo: replyTo?.id || null }))) {
      setText("");
      setReplyTo(null);
      onClearItemRef?.();
    }
  };

  const roots = path.comments.filter(c => !c.reply_to);
  const replies = id => path.comments.filter(c => c.reply_to === id);
  const open = path.comments.filter(c => !c.reply_to && !c.resolved).length;

  const renderComment = (c, nested = false) => (
    <div key={c.id} className={`comment ${nested ? "comment--reply" : ""} ${c.resolved ? "comment--resolved" : ""}`}>
      <div className="comment__head">
        <strong>{c.author?.name}</strong>
        <Badge tone={c.author?.role === "reviewer" ? "orange" : "purple"}>{t(`role_${c.author?.role}`)}</Badge>
        <span className="cell-sub">{formatDateTime(c.at, locale)}</span>
        {c.item_ref && <span className="item-chip">{c.item_ref.label}</span>}
      </div>
      <p>{c.text}</p>
      {!nested && canComment && (
        <div className="comment__actions">
          <button className="link-btn" onClick={() => setReplyTo(c)}>{t("reply")}</button>
          <button className="link-btn" onClick={() => run(() => resolveComment(path.id, c.id, !c.resolved))}>
            {c.resolved ? t("reopen") : t("mark_resolved")}
          </button>
        </div>
      )}
      {c.resolved && !nested && <span className="quote-check quote-check--ok"><CircleCheck size={12} /> {t("resolved_by", { name: c.resolved_by?.name || "—" })}</span>}
      {!nested && replies(c.id).map(r => renderComment(r, true))}
    </div>
  );

  return (
    <div className="path-comments">
      <p className="cell-sub">{t("comments_open", { n: open, total: roots.length })}</p>
      {roots.length === 0 && <p className="cell-sub">{t("comments_empty")}</p>}
      {roots.map(c => renderComment(c))}

      {canComment && (
        <div className="comment-form">
          {(itemRef || replyTo) && (
            <div className="chip-row">
              {itemRef && <span className="item-chip">{itemRef.label} <button aria-label={t("cancel")} onClick={onClearItemRef}><X size={11} /></button></span>}
              {replyTo && <span className="item-chip">{t("replying_to", { name: replyTo.author?.name })} <button aria-label={t("cancel")} onClick={() => setReplyTo(null)}><X size={11} /></button></span>}
            </div>
          )}
          <textarea rows={3} value={text} onChange={e => setText(e.target.value)} placeholder={t("comment_placeholder")} />
          {error && <div className="notice notice--danger"><CircleAlert size={16} /><span>{error}</span></div>}
          <div className="modal-actions" style={{ marginTop: 8 }}>
            <Button onClick={send} disabled={!text.trim()} icon={<Send size={14} />}>{t("send_comment")}</Button>
          </div>
        </div>
      )}
    </div>
  );
}
