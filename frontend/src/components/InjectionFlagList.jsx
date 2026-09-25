import { CircleCheck } from "./Icons";
import { Badge } from "./UI";
import { useLanguage } from "../contexts/LanguageContext";

/** Danh sách cờ prompt injection: luật khớp, vị trí (tài liệu · chunk · trang) và đoạn trích quanh chỗ khớp */
export default function InjectionFlagList({ flags }) {
  const { t } = useLanguage();
  if (!flags.length) return <p className="quote-check quote-check--ok"><CircleCheck size={13} /> {t("injection_none")}</p>;
  return (
    <div className="flag-list">
      {flags.map((f, i) => (
        <div key={`${f.chunk_id}-${i}`} className="flag-item">
          <div>
            <Badge tone={f.severity === "high" ? "red" : "orange"}>{t(`inj_rule_${f.rule_id}`)}</Badge>
            <span className="cell-sub">{f.doc ? `${f.doc} · ` : ""}{f.chunk_id}{f.page != null ? ` · ${t("page_abbr")}${f.page}` : ""}</span>
          </div>
          {f.excerpt && <code>{f.excerpt}</code>}
        </div>
      ))}
    </div>
  );
}
