import { CircleCheck, CircleAlert, ShieldAlert } from "../Icons";
import { Badge } from "../UI";
import { useLanguage } from "../../contexts/LanguageContext";
import { COVERAGE_THRESHOLDS } from "../../utils/pathChecks";

const FINAL_META = {
  verified: { tone: "green", icon: CircleCheck, label: "vtag_verified" },
  verified_warning: { tone: "orange", icon: CircleAlert, label: "vtag_warning" },
  manual_review: { tone: "red", icon: ShieldAlert, label: "vtag_manual_review" },
};

/** Một trong 3 trạng thái kiểm định: Verified / Verified with Warning / Manual Review Required */
export function FinalStatusBadge({ status, large = false }) {
  const { t } = useLanguage();
  const meta = FINAL_META[status] || FINAL_META.manual_review;
  const Icon = meta.icon;
  return (
    <span className={`final-status final-status--${meta.tone} ${large ? "final-status--lg" : ""}`}>
      <Icon size={large ? 18 : 13} /> {t(meta.label)}
    </span>
  );
}

const PATH_TONE = { draft: "default", in_review: "orange", changes_requested: "red", published: "green", archived: "default" };

export function PathStatusBadge({ status }) {
  const { t } = useLanguage();
  return <Badge tone={PATH_TONE[status] || "default"}>{t(`path_status_${status}`)}</Badge>;
}

function coverageTone(score) {
  if (score == null) return "default";
  if (score < COVERAGE_THRESHOLDS.manualBelow) return "red";
  if (score < COVERAGE_THRESHOLDS.warningBelow) return "orange";
  return "green";
}

export function CoverageScore({ score }) {
  if (score == null) return <Badge tone="default">—</Badge>;
  return (
    <span className="coverage-score">
      <Badge tone={coverageTone(score)}>{Math.round(score * 100)}%</Badge>
    </span>
  );
}

export function EngineBadge({ engine }) {
  const { t } = useLanguage();
  if (engine === "gemini") return <Badge tone="blue">{t("engine_gemini")}</Badge>;
  return <Badge tone="orange">{t("engine_local_draft")}</Badge>;
}
