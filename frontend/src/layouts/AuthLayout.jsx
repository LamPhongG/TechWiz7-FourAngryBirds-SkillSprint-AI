import { Outlet } from "react-router-dom";
import { Sparkles, ShieldCheck, WandSparkles, UserRound } from "../components/Icons";
import { useLanguage, LanguageToggle } from "../contexts/LanguageContext";

const ROLE_INTRO = [
  ["hr", WandSparkles],
  ["reviewer", ShieldCheck],
  ["employee", UserRound],
];

/** Nửa trái giới thiệu sản phẩm, nửa phải là nền gradient cho thẻ đăng nhập dạng kính */
export default function AuthLayout() {
  const { t } = useLanguage();
  return (
    <div className="auth-page">
      <section className="auth-visual">
        <div className="auth-brand">
          <div className="brand-mark"><Sparkles size={18} /></div>
          SkillSprint AI
        </div>
        <div className="auth-hero">
          <span className="eyebrow">{t("auth_eyebrow")}</span>
          <h1>{t("auth_title")}</h1>
          <p>{t("auth_desc")}</p>
          <ul className="auth-roles">
            {ROLE_INTRO.map(([role, Icon]) => (
              <li key={role}>
                <span className="auth-roles__icon"><Icon size={16} /></span>
                <div>
                  <strong>{t(`role_${role}`)}</strong>
                  <span>{t(`login_role_${role}_desc`)}</span>
                </div>
              </li>
            ))}
          </ul>
          <div className="auth-mini">
            <ShieldCheck size={18} />
            <span>{t("auth_mini")}</span>
          </div>
        </div>
      </section>

      <section className="auth-glass">
        <span className="glass-blob glass-blob--1" aria-hidden="true" />
        <span className="glass-blob glass-blob--2" aria-hidden="true" />
        <span className="glass-blob glass-blob--3" aria-hidden="true" />
        <LanguageToggle className="glass-lang" />
        <Outlet />
      </section>
    </div>
  );
}
