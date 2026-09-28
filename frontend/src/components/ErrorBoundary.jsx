import React, { Component } from "react";
import { useLocation } from "react-router-dom";
import { en } from "../locales/en";

// Outside LanguageProvider (which itself might fail), so read directly from en
function text(key) {
  return en[key] ?? key;
}

async function resetDemoData() {
  try {
    Object.keys(localStorage).filter(k => k.startsWith("skillsprint.")).forEach(k => localStorage.removeItem(k));
    sessionStorage.clear();
  } catch {
    // Storage blocked — nothing to clear
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

/** Catches render errors to prevent white-screen crashes; re-attempts render on route navigation */
export default function ErrorBoundary({ children, inline = false }) {
  const { pathname } = useLocation();
  return <Boundary key={pathname} inline={inline}>{children}</Boundary>;
}

