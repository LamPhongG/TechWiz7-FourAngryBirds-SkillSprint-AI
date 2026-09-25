import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { BrainCircuit, Check, WandSparkles, CircleAlert, ShieldAlert, Loader2, ArrowRight } from "../../components/Icons";
import { Card, Badge, Button } from "../../components/UI";
import { EngineBadge } from "../../components/path/Badges";
import { PATH_PURPOSES, ROLES, SKILL_LEVELS } from "../../data/company";
import { useLanguage } from "../../contexts/LanguageContext";
import { useDocuments } from "../../contexts/DocumentsContext";
import { usePaths, PathError } from "../../contexts/PathsContext";
import { backendEnabled } from "../../services/apiClient";
import { PROMPT_VERSION } from "../../services/pipelineService";

/** HR chọn vị trí + tài liệu nguồn → AI sinh bản nháp lộ trình → mở trang chi tiết để xem, sửa và gửi duyệt */
export default function CreatePath() {
  const { activeDocuments, processed, progress } = useDocuments();
  const { createPath } = usePaths();
  const navigate = useNavigate();
  const { t, tv, pick } = useLanguage();

  const [roleId, setRoleId] = useState(ROLES[6].id);
  const [level, setLevel] = useState("Intermediate");
  const [purpose, setPurpose] = useState("onboarding");
  const [prompt, setPrompt] = useState("");
  const [selectedIds, setSelectedIds] = useState([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const role = ROLES.find(r => r.id === roleId);
  const ready = activeDocuments.filter(d => d.processing === "done");
  const sources = ready.filter(d => selectedIds.includes(d.id));
  const flagged = sources.filter(d => d.injectionFlagCount > 0);
  const notReady = activeDocuments.filter(d => d.processing !== "done");

  const toggle = id => setSelectedIds(ids => (ids.includes(id) ? ids.filter(x => x !== id) : [...ids, id]));
  const selectAll = () => setSelectedIds(ready.map(d => d.id));

  const generate = async () => {
    setError("");
    setBusy(true);
    try {
      const path = await createPath({ role, level, purpose, sourceDocs: sources, processed, prompt: prompt.trim() });
      navigate(`/hr/paths/${path.id}`);
    } catch (e) {
      setError(e instanceof PathError ? t(e.key, e.vars) : e.message === "NO_CONTENT" ? t("err_no_content") : e.message);
      setBusy(false);
    }
  };

  return (
    <div>
      <div className="page-heading">
        <div>
          <span className="eyebrow">{t("generative_ai_engine")}</span>
          <h1>{t("create_path_title")}</h1>
          <p>{t("create_path_desc")}</p>
        </div>
        <div className="heading-actions">
          <Badge tone="purple">{t("prompt_version")}: {PROMPT_VERSION}</Badge>
          <EngineBadge engine={backendEnabled() ? "gemini" : "local-draft"} />
        </div>
      </div>

      <div className="flow-steps">
        {["flow_step_upload", "flow_step_generate", "flow_step_review", "flow_step_publish", "flow_step_learn"].map((k, i) => (
          <span key={k} className={i === 1 ? "is-current" : ""}>{i > 0 && <ArrowRight size={13} />}{t(k)}</span>
        ))}
      </div>

      <div className="ai-studio-grid">
        <Card>
          <div className="ai-header">
            <div className="ai-icon"><BrainCircuit size={22} /></div>
            <div><h3>{t("config_title")}</h3><p>{t("config_desc")}</p></div>
          </div>
          <div className="form-grid" style={{ marginBottom: 12 }}>
            <label>{t("role_position")}
              <select value={roleId} onChange={e => setRoleId(e.target.value)}>
                {ROLES.map(r => <option key={r.id} value={r.id}>{pick(r, "name")}</option>)}
              </select>
            </label>
            <label>{t("path_purpose")}
              <select value={purpose} onChange={e => setPurpose(e.target.value)}>
                {PATH_PURPOSES.map(p => <option key={p} value={p}>{t(`purpose_${p}`)}</option>)}
              </select>
            </label>
            <label>{t("skill_level")}
              <select value={level} onChange={e => setLevel(e.target.value)}>
                {SKILL_LEVELS.map(l => <option key={l} value={l}>{tv(l)}</option>)}
              </select>
            </label>
            <label>{t("department")}<input value={tv(role.department)} readOnly /></label>
            <label style={{ gridColumn: "1 / -1" }}>{t("system_prompt")}
              <textarea value={prompt} onChange={e => setPrompt(e.target.value)} placeholder={t("ai_default_prompt")} style={{ height: 70 }} />
            </label>
          </div>
          <p className="cell-sub">{t(`purpose_${purpose}_desc`)}</p>
        </Card>

        <Card>
          <div className="field-label" style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <span>{t("ground_truth_source")}</span>
            <span style={{ display: "flex", gap: 8, alignItems: "center" }}>
              {ready.length > 0 && <button type="button" className="link-btn" onClick={selectAll}>{t("select_all_ready_docs")}</button>}
              <Badge tone="green">{sources.length} {t("docs_selected")}</Badge>
            </span>
          </div>
          {activeDocuments.length === 0 ? (
            <div className="notice notice--warning">
              <CircleAlert size={16} />
              <span>{t("ai_no_sources")} <button type="button" className="link-btn" onClick={() => navigate("/hr/documents")}>{t("upload_documents")}</button></span>
            </div>
          ) : (
            <div className="source-select">
              {activeDocuments.map(d => {
                const selected = selectedIds.includes(d.id);
                const disabled = d.processing !== "done";
                return (
                  <button className={selected ? "selected" : ""} disabled={disabled} onClick={() => toggle(d.id)} key={d.id} title={disabled ? t("source_not_ready") : undefined}>
                    <span>{selected && <Check size={13} />}</span>
                    <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-start" }}>
                      <span className="source-select__title">{d.code} · {pick(d, "title")}</span>
                      <span className="source-select__sub">
                        {tv(d.category)} · v{d.version}
                        {progress[d.id] && <b className="text-warning"> · {t(`proc_stage_${progress[d.id].stage}`)}</b>}
                        {!progress[d.id] && disabled && <b className="text-warning"> · {t(d.processing === "failed" ? "proc_failed" : "processing_pending")}</b>}
                        {d.injectionFlagCount > 0 && <b className="text-danger"> · {t("flag_injection")}</b>}
                      </span>
                    </div>
                  </button>
                );
              })}
            </div>
          )}

          {flagged.length > 0 && (
            <div className="notice notice--danger"><ShieldAlert size={16} /><span>{t("injection_excluded_warning", { list: flagged.map(d => d.code).join(", ") })}</span></div>
          )}
          {notReady.length > 0 && (
            <div className="notice notice--warning"><CircleAlert size={16} /><span>{t("sources_not_ready_warning", { n: notReady.length })}</span></div>
          )}
          {error && <div className="notice notice--danger"><CircleAlert size={16} /><span>{error}</span></div>}

          <Button onClick={generate} disabled={busy || sources.length === 0}
            icon={busy ? <Loader2 size={16} className="spin" /> : <WandSparkles size={16} />}
            style={{ width: "100%", marginTop: 10, height: 44, fontSize: 14 }}>
            {busy ? t("generating_btn") : t("generate_btn")}
          </Button>
        </Card>
      </div>
    </div>
  );
}
