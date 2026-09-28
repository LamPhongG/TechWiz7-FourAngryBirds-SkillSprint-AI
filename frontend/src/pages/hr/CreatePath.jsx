import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { BrainCircuit, Check, WandSparkles, CircleAlert, ShieldAlert, Loader2, ArrowRight, LockKeyhole, Info } from "../../components/Icons";
import { Card, Badge, Button } from "../../components/UI";
import { EngineBadge } from "../../components/path/Badges";
import GenerationProgress from "../../components/path/GenerationProgress";
import { DEFAULT_ONBOARDING_DAYS, ONBOARDING_DURATIONS, PATH_PURPOSES, ROLES, SKILL_LEVELS } from "../../data/company";
import { useLanguage } from "../../contexts/LanguageContext";
import { useDocuments } from "../../contexts/DocumentsContext";
import { usePaths, PathError } from "../../contexts/PathsContext";
import { apiRequest, backendEnabled } from "../../services/apiClient";
import { PROMPT_VERSION } from "../../services/pipelineService";

const NO_MATRIX = { roleId: null, list: [], loading: false, error: "" };
const DONE_PAUSE_MS = 1200;

/**
 * Role requirement matrix: mandatory documents preselected.
 * Backend mode only — matrix resides on server. HR may deselect, but the server only accepts
 * if `allow_missing_mandatory` is confirmed, and Reviewer always sees missing mandatory warnings.
 */
function useRequiredSources(roleId, readyKey) {
  const [state, setState] = useState(NO_MATRIX);
  useEffect(() => {
    if (!backendEnabled()) return undefined;
    let cancelled = false;
    setState(s => ({ ...s, roleId, loading: true, error: "" }));
    apiRequest(`/job-positions/${roleId}/required-sources`)
      .then(list => { if (!cancelled) setState({ roleId, list, loading: false, error: "" }); })
      .catch(e => { if (!cancelled) setState({ roleId, list: [], loading: false, error: e.message }); });
    return () => { cancelled = true; };
    // readyKey: newly processed document can change the "ready" status of a mandatory document
  }, [roleId, readyKey]);
  return state;
}

/** HR selects role + source documents -> AI drafts path -> opens detail page for review, edit, and submission */
export default function CreatePath() {
  const { activeDocuments, processed, progress } = useDocuments();
  const { createPath } = usePaths();
  const navigate = useNavigate();
  const { t, tv, pick } = useLanguage();

  const [roleId, setRoleId] = useState(ROLES[6].id);
  const [level, setLevel] = useState("Intermediate");
  const [purpose, setPurpose] = useState("onboarding");
  const [durationDays, setDurationDays] = useState(DEFAULT_ONBOARDING_DAYS);
  const [prompt, setPrompt] = useState("");
  // Manually added documents, and mandatory documents deselected by HR
  const [extraIds, setExtraIds] = useState([]);
  const [omittedIds, setOmittedIds] = useState([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [job, setJob] = useState(null);

  const role = ROLES.find(r => r.id === roleId);
  const ready = activeDocuments.filter(d => d.processing === "done");
  const readyKey = ready.map(d => d.id).join(",");
  const matrix = useRequiredSources(roleId, readyKey);
  const matrixReady = !backendEnabled() || (matrix.roleId === roleId && !matrix.loading);

  const { mandatoryIds, byDocId, unavailable, outdated } = useMemo(() => {
    const mandatory = new Set();
    const map = {};
    for (const s of matrix.list) {
      if (!s.document) continue;
      map[s.document.id] = s;
      if (s.mandatory && s.status === "ready") mandatory.add(s.document.id);
    }
    return {
      mandatoryIds: mandatory,
      byDocId: map,
      unavailable: matrix.list.filter(s => s.mandatory && s.status !== "ready"),
      outdated: matrix.list.filter(s => s.outdated_requirement_ids.length > 0),
    };
  }, [matrix.list]);

  const selectedIds = new Set([...[...mandatoryIds].filter(id => !omittedIds.includes(id)), ...extraIds]);
  const omittedCodes = omittedIds.filter(id => mandatoryIds.has(id)).map(id => byDocId[id].code);
  const sources = ready.filter(d => selectedIds.has(d.id));
  const flagged = sources.filter(d => d.injectionFlagCount > 0);
  const notReady = activeDocuments.filter(d => d.processing !== "done");
  // Mandatory first, then matrix suggested documents, followed by remaining documents
  const rank = d => (mandatoryIds.has(d.id) ? 0 : byDocId[d.id] ? 1 : 2);
  const listed = [...activeDocuments].sort((a, b) => rank(a) - rank(b));

  const flip = (ids, id) => (ids.includes(id) ? ids.filter(x => x !== id) : [...ids, id]);
  const changeRole = id => { setRoleId(id); setExtraIds([]); setOmittedIds([]); };
  const toggle = id => (mandatoryIds.has(id) ? setOmittedIds(ids => flip(ids, id)) : setExtraIds(ids => flip(ids, id)));
  const restoreMandatory = () => setOmittedIds([]);
  const selectAll = () => { setExtraIds(ready.map(d => d.id)); setOmittedIds([]); };

  const generate = async () => {
    setError("");
    setJob(null);
    setBusy(true);
    try {
      const path = await createPath({ role, level, purpose, durationDays, sourceDocs: sources, processed, prompt: prompt.trim(),
        allowMissingMandatory: omittedCodes.length > 0, onProgress: setJob });
      // Allow HR to see all steps completed before transitioning to draft
      if (backendEnabled()) await new Promise(resolve => setTimeout(resolve, DONE_PAUSE_MS));
      navigate(`/hr/paths/${path.id}`);
    } catch (e) {
      setError(e instanceof PathError ? t(e.key, e.vars) : e.message === "NO_CONTENT" ? t("err_no_content") : e.message);
      // Browser mode without progress screen: error displayed directly below button as before
      if (!backendEnabled()) setBusy(false);
    }
  };
  const backToConfig = () => { setBusy(false); setJob(null); setError(""); };

  if (busy && backendEnabled()) {
    const subtitle = [
      pick(role, "name"), t(`purpose_${purpose}`),
      purpose === "onboarding" ? t(`duration_${durationDays}`) : null,
      t("gp_sources_count", { n: sources.length }),
    ].filter(Boolean).join(" · ");
    return (
      <div>
        <div className="page-heading">
          <div>
            <span className="eyebrow">{t("generative_ai_engine")}</span>
            <h1>{t("create_path_title")}</h1>
          </div>
          <div className="heading-actions"><Badge tone="purple">{t("prompt_version")}: {PROMPT_VERSION}</Badge></div>
        </div>
        <GenerationProgress job={job} subtitle={subtitle} error={error} onBack={backToConfig} />
      </div>
    );
  }

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
              <select value={roleId} onChange={e => changeRole(e.target.value)}>
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

          {purpose === "onboarding" ? (
            <div className="duration-picker">
              <span className="field-label">{t("path_duration")}</span>
              <div className="duration-options" role="radiogroup" aria-label={t("path_duration")}>
                {Object.entries(ONBOARDING_DURATIONS).map(([days, stages]) => (
                  <button key={days} type="button" role="radio" aria-checked={durationDays === Number(days)}
                    className={durationDays === Number(days) ? "selected" : ""} onClick={() => setDurationDays(Number(days))}>
                    <strong>{t(`duration_${days}`)}</strong>
                    <small>{stages.map(k => t(`stage_${k}`)).join(" → ")}</small>
                  </button>
                ))}
              </div>
              <p className="cell-sub">{t("path_duration_hint")}</p>
            </div>
          ) : (
            <p className="cell-sub">{t("path_duration_promotion")}</p>
          )}
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

          {backendEnabled() ? (
            matrix.error ? (
              <div className="notice notice--danger"><CircleAlert size={16} /><span>{t("matrix_load_failed", { error: matrix.error })}</span></div>
            ) : matrixReady && (
              <div className="notice notice--info">
                <LockKeyhole size={16} />
                <span>{mandatoryIds.size > 0 ? t("matrix_mandatory_selected", { n: mandatoryIds.size, role: pick(role, "name") }) : t("matrix_no_mandatory", { role: pick(role, "name") })}</span>
              </div>
            )
          ) : (
            <div className="notice notice--info"><Info size={16} /><span>{t("matrix_backend_only")}</span></div>
          )}
          {omittedCodes.length > 0 && (
            <div className="notice notice--warning" role="alert">
              <CircleAlert size={16} />
              <span>
                {t("mandatory_omitted_warning", { list: omittedCodes.join(", ") })}{" "}
                <button type="button" className="link-btn" onClick={restoreMandatory}>{t("mandatory_restore_all")}</button>
              </span>
            </div>
          )}
          {unavailable.length > 0 && (
            <div className="notice notice--warning">
              <CircleAlert size={16} />
              <span>{t("mandatory_unavailable_warning", { list: unavailable.map(s => `${s.code} (${t(`required_status_${s.status}`)})`).join(", ") })}</span>
            </div>
          )}
          {outdated.length > 0 && (
            <div className="notice notice--info">
              <Info size={16} />
              <span>{t("matrix_outdated_rows", { n: outdated.reduce((sum, s) => sum + s.outdated_requirement_ids.length, 0), list: outdated.map(s => s.code).join(", ") })}</span>
            </div>
          )}

          {activeDocuments.length === 0 ? (
            <div className="notice notice--warning">
              <CircleAlert size={16} />
              <span>{t("ai_no_sources")} <button type="button" className="link-btn" onClick={() => navigate("/hr/documents")}>{t("upload_documents")}</button></span>
            </div>
          ) : (
            <div className="source-select">
              {listed.map(d => {
                const selected = selectedIds.has(d.id);
                const mandatory = mandatoryIds.has(d.id);
                const matrixEntry = byDocId[d.id];
                const disabled = d.processing !== "done";
                return (
                  <button className={`${selected ? "selected" : ""} ${mandatory ? (selected ? "is-mandatory" : "is-omitted") : ""}`}
                    disabled={disabled} aria-pressed={selected} onClick={() => toggle(d.id)} key={d.id}
                    title={disabled ? t("source_not_ready") : mandatory ? t("source_mandatory_hint") : undefined}>
                    <span>{selected && <Check size={13} />}</span>
                    <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-start" }}>
                      <span className="source-select__title">
                        {d.code} · {pick(d, "title")}
                        {matrixEntry && (matrixEntry.mandatory
                          ? <b className="source-tag source-tag--mandatory">{t("source_mandatory", { n: matrixEntry.mandatory_requirement_ids.length })}</b>
                          : <b className="source-tag source-tag--optional">{t("source_matrix_optional", { n: matrixEntry.requirement_ids.length })}</b>)}
                      </span>
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

          <Button onClick={generate} disabled={busy || sources.length === 0 || !matrixReady}
            icon={busy || !matrixReady ? <Loader2 size={16} className="spin" /> : <WandSparkles size={16} />}
            style={{ width: "100%", marginTop: 10, height: 44, fontSize: 14 }}>
            {busy ? t("generating_btn") : t("generate_btn")}
          </Button>
        </Card>
      </div>
    </div>
  );
}
