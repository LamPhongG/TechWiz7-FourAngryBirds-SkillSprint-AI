import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Sparkles, Eye, EyeOff, CircleAlert, Info } from "../../components/Icons";
import { useAuth, HOME_PATH, DEMO_ACCOUNTS, DEMO_PASSWORD } from "../../hooks/useAuth";
import { useLanguage } from "../../contexts/LanguageContext";

export default function Login() {
  const navigate = useNavigate();
  const { login } = useAuth();
  const { t } = useLanguage();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [remember, setRemember] = useState(false);
  const [note, setNote] = useState(null);
  const [error, setError] = useState("");

  const submit = async (e) => {
    e.preventDefault();
    if (!email.trim() || !password) {
      setError(t("login_error_empty"));
      return;
    }
    let role;
    try {
      role = await login(email, password, { remember });
    } catch {
      setError(t("err_network"));
      return;
    }
    if (!role) {
      setError(t("login_error_invalid"));
      return;
    }
    navigate(HOME_PATH[role]);
  };

  const fillDemo = (account) => {
    setEmail(account.email);
    setPassword(DEMO_PASSWORD);
    setError("");
  };

  const toggleNote = key => setNote(current => (current === key ? null : key));

  return (
    <form className="glass-card" onSubmit={submit} noValidate>
      <div className="glass-card__brand"><span className="brand-mark" style={{ overflow: "hidden" }}><img src="/logonhom.png" alt="Logo" style={{ height: "100%", width: "100%", objectFit: "cover" }} /></span> SkillSprint AI</div>
      <h2>{t("login_title")}</h2>
      <p className="glass-card__subtitle">{t("login_subtitle")}</p>

      {/* placeholder=" " enables CSS :placeholder-shown to float label */}
      <div className="glass-float">
        <input id="login-email" type="email" autoComplete="username" placeholder=" " value={email}
          aria-invalid={!!error} onChange={e => { setEmail(e.target.value); setError(""); }} />
        <label htmlFor="login-email">{t("login_email")}</label>
      </div>

      <div className="glass-float">
        <input id="login-password" type={showPassword ? "text" : "password"} autoComplete="current-password" placeholder=" "
          value={password} aria-invalid={!!error} onChange={e => { setPassword(e.target.value); setError(""); }} />
        <label htmlFor="login-password">{t("login_password")}</label>
        <button type="button" className="glass-eye" onClick={() => setShowPassword(v => !v)}
          aria-label={t(showPassword ? "login_hide_password" : "login_show_password")}>
          {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
        </button>
      </div>

      <div className="glass-row">
        <label className="glass-check">
          <input type="checkbox" checked={remember} onChange={e => setRemember(e.target.checked)} />
          {t("login_remember")}
        </label>
        <button type="button" className="glass-link" onClick={() => toggleNote("forgot")}>{t("login_forgot")}</button>
      </div>

      {error && <p className="glass-error" role="alert"><CircleAlert size={15} /> {error}</p>}

      <button type="submit" className="glass-btn">{t("login_submit")}</button>

      <p className="glass-register">
        {t("login_no_account")}{" "}
        <button type="button" onClick={() => toggleNote("account")}>{t("login_contact_hr")}</button>
      </p>
      {note && <p className="glass-note"><Info size={14} /> {t(note === "forgot" ? "login_forgot_hint" : "login_account_hint")}</p>}

      <div className="glass-demo">
        <span>{t("login_demo_accounts")}</span>
        <div style={{ display: "flex", flexWrap: "wrap", gap: "6px", marginTop: "8px" }}>
          {DEMO_ACCOUNTS.map(a => (
            <button key={a.email} type="button" className="glass-chip" onClick={() => fillDemo(a)} title={a.email}>
              {a.label || t(`role_${a.roleKey}`)}
            </button>
          ))}
        </div>
        <small style={{ display: "block", marginTop: "8px" }}>{t("login_demo_note", { password: DEMO_PASSWORD })}</small>
      </div>
    </form>
  );
}
