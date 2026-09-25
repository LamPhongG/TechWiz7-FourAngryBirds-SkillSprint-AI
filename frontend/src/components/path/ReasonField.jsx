import { useLanguage } from "../../contexts/LanguageContext";
import { MIN_REASON_LENGTH } from "../../utils/pathChecks";

export function ReasonField({ value, onChange, required = false, label }) {
  const { t } = useLanguage();
  const len = value.trim().length;
  return (
    <label className="reason-field">
      {label || t(required ? "reason_label_required" : "reason_label_optional")}
      <textarea value={value} onChange={e => onChange(e.target.value)} rows={3} placeholder={t("reason_placeholder")} />
      {required && <span className={`cell-sub ${len < MIN_REASON_LENGTH ? "text-danger" : ""}`}>{t("reason_counter", { n: len, min: MIN_REASON_LENGTH })}</span>}
    </label>
  );
}
