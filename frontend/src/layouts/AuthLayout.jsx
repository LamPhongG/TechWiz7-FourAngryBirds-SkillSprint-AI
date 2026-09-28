import { Outlet } from "react-router-dom";
import { useLanguage } from "../contexts/LanguageContext";

/** Left side showcases product visuals, right side features glassmorphism login card */
export default function AuthLayout() {
  const { t } = useLanguage();
  return (
    <div className="auth-page">
      <section className="auth-visual">
        <video autoPlay loop muted playsInline className="auth-video-bg">
          <source src="/videocym.mp4" type="video/mp4" />
        </video>
        <div className="auth-overlay"></div>
        <div className="auth-brand">
          <img src="/logonhom.png" alt="Logo" className="auth-logo-icon" style={{ borderRadius: "8px", objectFit: "cover" }} />
          SkillSprint AI
        </div>
        <div className="auth-hero">
          <span className="eyebrow">{t("auth_eyebrow")}</span>
          <h1>{t("auth_title")}</h1>
        </div>
      </section>

      <section className="auth-glass">
        <span className="glass-blob glass-blob--1" aria-hidden="true" />
        <span className="glass-blob glass-blob--2" aria-hidden="true" />
        <span className="glass-blob glass-blob--3" aria-hidden="true" />
        <Outlet />
      </section>
    </div>
  );
}
