import { createContext, useContext, useState, useEffect, useCallback, useMemo } from "react";
import { en } from "../locales/en";

const translations = { en };
const DEFAULT_LANG = "en";
const FALLBACK_LANG = "en";
const STORAGE_KEY = "app_lang";

const LanguageContext = createContext(null);

export const LanguageProvider = ({ children }) => {
  const [lang, setLang] = useState("en");

  useEffect(() => {
    document.documentElement.lang = "en";
    try {
      localStorage.setItem(STORAGE_KEY, "en");
    } catch {
      // Storage unavailable (e.g. private mode)
    }
  }, []);

  // t("key", { name: "Alex" }) — interpolate variables; fallback to key if missing
  const t = useCallback((key, vars) => {
    let text = translations.en?.[key] ?? key;
    if (vars) {
      text = text.replace(/\{(\w+)\}/g, (match, name) => (vars[name] ?? match));
    }
    return text;
  }, []);

  // Translate data values (status, department, etc.): tv("Human Resources") → key "v_human_resources"
  const tv = useCallback((value) => {
    if (value == null) return "";
    const key = `v_${String(value).toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_|_$/g, "")}`;
    return translations.en?.[key] ?? value;
  }, []);

  const toggleLanguage = useCallback(() => {}, []);

  // Pick language field: prioritize English variant if exists
  const pick = useCallback((item, field) => {
    if (!item) return "";
    return item[`${field}En`] ?? item[field] ?? "";
  }, []);

  const locale = "en-US";

  const value = useMemo(
    () => ({ lang, locale, t, tv, pick, toggleLanguage }),
    [lang, locale, t, tv, pick, toggleLanguage]
  );

  return (
    <LanguageContext.Provider value={value}>
      {children}
    </LanguageContext.Provider>
  );
};

export const useLanguage = () => {
  const ctx = useContext(LanguageContext);
  if (!ctx) {
    const lang = "en";
    const t = (key, vars) => {
      let text = translations.en?.[key] ?? key;
      if (vars) text = text.replace(/\{(\w+)\}/g, (match, name) => (vars[name] ?? match));
      return text;
    };
    const tv = val => val || "";
    const pick = (item, field) => item ? (item[`${field}En`] ?? item[field] ?? "") : "";
    return { lang, locale: "en-US", t, tv, pick, toggleLanguage: () => {} };
  }
  return ctx;
};

export function LanguageToggle() {
  // Pure English mode - no language toggle required
  return null;
}

