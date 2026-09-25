import { useLanguage } from "../contexts/LanguageContext";

// Trạng thái kiểm tra kiến thức của từng mục trong lộ trình (utils/pathChecks.js → checkKnowledge)
const STATUS_CONFIG = {
  verified: { icon: "✓", tone: "verified", label: "vtag_verified", description: "vtag_verified_desc" },
  outdated_source: { icon: "⚠", tone: "warning", label: "vtag_outdated_source", description: "vtag_outdated_source_desc" },
  source_missing: { icon: "✗", tone: "danger", label: "vtag_source_missing", description: "vtag_source_missing_desc" },
  hallucination: { icon: "✗", tone: "danger", label: "vtag_hallucination", description: "vtag_hallucination_desc" },
  contradiction: { icon: "✗", tone: "danger", label: "vtag_contradiction", description: "vtag_contradiction_desc" },
  pending: { icon: "○", tone: "pending", label: "vtag_pending", description: "vtag_pending_desc" },
};

export default function ValidationTag({ status = "pending", showLabel = true }) {
  const { t } = useLanguage();
  const config = STATUS_CONFIG[status] || STATUS_CONFIG.pending;
  return (
    <span className={`vtag vtag--${config.tone}`} title={t(config.description)}>
      <span className="vtag__icon">{config.icon}</span>
      {showLabel && <span className="vtag__label">{t(config.label)}</span>}
    </span>
  );
}
