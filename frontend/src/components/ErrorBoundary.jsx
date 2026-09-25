import { Component } from "react";
import { useLocation } from "react-router-dom";
import { en } from "../locales/en";
import { vi } from "../locales/vi";

// Nằm ngoài LanguageProvider (provider cũng có thể là chỗ lỗi) nên tự đọc ngôn ngữ đã lưu
function text(key) {
  let lang = "vi";
  try {
    if (localStorage.getItem("app_lang") === "en") lang = "en";
  } catch {
    // Storage bị chặn — dùng tiếng Việt
  }
  return (lang === "en" ? en : vi)[key] ?? en[key] ?? key;
}

async function resetDemoData() {
  try {
    Object.keys(localStorage).filter(k => k.startsWith("skillsprint.")).forEach(k => localStorage.removeItem(k));
    sessionStorage.clear();
  } catch {
    // Storage bị chặn — không có gì để xoá
  }
  await new Promise(resolve => {
    if (typeof indexedDB === "undefined") return resolve();
    const req = indexedDB.deleteDatabase("skillsprint-ai");
    req.onsuccess = req.onerror = req.onblocked = () => resolve();
  });
  window.location.assign("/login");
}

class Boundary extends Component {
  state = { error: null };

  static getDerivedStateFromError(error) {
    return { error };
  }

  componentDidCatch(error, info) {
    console.error("SkillSprint UI error:", error, info.componentStack);
  }

  render() {
    const { error } = this.state;
    if (!error) return this.props.children;
    return (
      <div className={this.props.inline ? "crash crash--inline" : "crash"}>
        <div className="crash__box">
          <h1>{text("crash_title")}</h1>
          <p>{text("crash_desc")}</p>
          <code>{error.message}</code>
          <div className="crash__actions">
            <button className="btn btn-secondary" onClick={() => window.location.reload()}>{text("crash_reload")}</button>
            <button className="btn btn-secondary" onClick={() => window.location.assign("/login")}>{text("crash_login")}</button>
            <button className="btn btn-danger" onClick={resetDemoData}>{text("crash_reset")}</button>
          </div>
          <p className="crash__hint">{text("crash_reset_hint")}</p>
        </div>
      </div>
    );
  }
}

/** Bắt lỗi render để không trắng trang; chuyển sang trang khác thì thử render lại từ đầu */
export default function ErrorBoundary({ children, inline = false }) {
  const { pathname } = useLocation();
  return <Boundary key={pathname} inline={inline}>{children}</Boundary>;
}
