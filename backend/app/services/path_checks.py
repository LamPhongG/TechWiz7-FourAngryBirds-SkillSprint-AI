"""Ground-truth checks of a learning path (server copy of frontend `utils/pathChecks.js`).

The browser runs the same checks for display; the server re-runs them when a path is submitted or
approved, so a publish decision never depends on what the client claims.
Pure Python, no AI (Rules section 3).
"""
import difflib
import re
from dataclasses import dataclass, field
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.injection_filter import scan_chunks
from app.genai_pipeline.text import normalize_for_match
from app.genai_pipeline.types import STAGE_TEMPLATES
from app.models import Document, DocumentChunk, FinalStatus, LearningPath
from app.services import role_matrix
from app.services.documents import compute_lifecycle

COVERAGE_MANUAL_BELOW = 0.6
# SRS 1.2 and NFR 4: a plan is Verified only when every mandatory requirement is covered.
COVERAGE_WARNING_BELOW = 1.0
CRITICAL_KNOWLEDGE = {"hallucination", "contradiction", "source_missing"}
WARNING_KNOWLEDGE = {"outdated_source", "pending"}


@dataclass
class _Doc:
    id: str
    code: str
    status: str


@dataclass
class CheckResult:
    knowledge: list[dict]
    flow: list[dict]
    injection: list[dict]
    coverage_score: float | None
    final_status: FinalStatus
    blocking: bool
    reasons: list[dict] = field(default_factory=list)
    mandatory_missing: list[str] = field(default_factory=list)
    duplicates: list[dict] = field(default_factory=list)

    def summary(self) -> dict:
        counts: dict[str, int] = {}
        for k in self.knowledge:
            counts[k["status"]] = counts.get(k["status"], 0) + 1
        return {
            "final_status": self.final_status.value,
            "blocking": self.blocking,
            "reasons": self.reasons,
            "knowledge": counts,
            "flow_errors": sum(1 for f in self.flow if f["severity"] == "error"),
            "flow_warnings": sum(1 for f in self.flow if f["severity"] == "warning"),
            "injection": len(self.injection),
            "duplicates": len(self.duplicates),
            "coverage_score": self.coverage_score,
            "mandatory_missing": self.mandatory_missing,
        }


def iter_items(stages: list[dict]):
    """Every lesson, task and quiz question of a path, with its module and source reference."""
    for stage in stages:
        for m in stage.get("modules", []):
            for kind, key in (("lesson", "lessons"), ("task", "tasks"), ("quiz", "quiz")):
                for item in m.get(key, []):
                    yield {"id": item.get("id"), "module_id": m.get("id"), "kind": kind, "item": item,
                           "source_reference": item.get("source_reference")}


def _find_doc(ref: dict, docs: list[_Doc]) -> _Doc | None:
    return (next((d for d in docs if d.id == ref.get("doc_id")), None)
            or next((d for d in docs if d.code == ref.get("doc") and d.status == "active"), None)
            or next((d for d in docs if d.code == ref.get("doc")), None))


def _find_quote(quote: str, chunks: list[dict], page: int | None) -> dict | None:
    needle = normalize_for_match(quote)
    if not needle:
        return None
    hits = [c for c in chunks if needle in c["norm"]]
    return next((c for c in hits if page is not None and c["page"] == page), hits[0] if hits else None)


def check_knowledge(stages: list[dict], docs: list[_Doc], chunks_by_doc: dict[str, list[dict]]) -> list[dict]:
    out = []
    for entry in iter_items(stages):
        ref = entry["source_reference"] or {}
        status = "verified"
        quote = (ref.get("exact_quote") or "").strip()
        doc = _find_doc(ref, docs) if quote else None
        if not quote or doc is None:
            status = "source_missing"
        elif not chunks_by_doc.get(doc.id):
            status = "pending"
        elif _find_quote(quote, chunks_by_doc[doc.id], ref.get("page")) is None:
            status = "hallucination"
        elif entry["kind"] == "quiz" and not _answer_in_quote(entry["item"], quote):
            # The question would grade on something the document does not say.
            status = "contradiction"
        elif doc.status != "active":
            status = "outdated_source"
        out.append({"id": entry["id"], "module_id": entry["module_id"], "kind": entry["kind"], "status": status})
    return out


def _answer_in_quote(question: dict, quote: str) -> bool:
    options, answer = question.get("options") or [], question.get("answer")
    if not isinstance(answer, int) or not 0 <= answer < len(options):
        return False
    return normalize_for_match(options[answer]) in normalize_for_match(quote)


def check_flow(purpose: str, stages: list[dict]) -> list[dict]:
    issues: list[dict] = []
    template = STAGE_TEMPLATES.get(purpose, STAGE_TEMPLATES["onboarding"])

    last = -1
    for s in stages:
        idx = template.index(s["key"]) if s["key"] in template else -1
        if idx < 0:
            issues.append({"severity": "error", "key": "flow_unknown_stage", "vars": {"stage": s["key"]}})
        elif idx <= last:
            issues.append({"severity": "error", "key": "flow_stage_order", "vars": {"stage": s["key"]}})
        last = max(last, idx)
        if not s.get("modules"):
            issues.append({"severity": "warning", "key": "flow_empty_stage", "vars": {"stage": s["key"]}})

    modules = [(m, si) for si, s in enumerate(stages) for m in s.get("modules", [])]
    if not modules:
        issues.append({"severity": "error", "key": "flow_no_modules"})

    seen_docs: set[str] = set()
    # Teach before you test: what the learner has been taught so far, in study order.
    taught: set[str] = set()
    for m, _si in modules:
        taught |= _taught_chunks(m)
        title = m.get("titleEn") or m.get("title")
        assessment = m.get("kind") == "assessment"
        if not assessment and not m.get("lessons"):
            issues.append({"severity": "error", "key": "flow_module_empty", "vars": {"module": title}, "module_id": m["id"]})
        if not assessment and not m.get("quiz"):
            issues.append({"severity": "warning", "key": "flow_no_quiz", "vars": {"module": title}, "module_id": m["id"]})
        for q in m.get("quiz", []):
            opts, ans = q.get("options"), q.get("answer")
            if not isinstance(opts, list) or len(opts) < 2 or not isinstance(ans, int) or not 0 <= ans < len(opts):
                issues.append({"severity": "error", "key": "flow_quiz_invalid", "vars": {"module": title}, "module_id": m["id"]})
        # Without completion criteria nobody can tell whether the task was done; a missing source is caught by
        # the knowledge check (source_missing).
        for t in m.get("tasks", []):
            if not str(t.get("completion_criteria") or "").strip():
                issues.append({"severity": "error", "key": "flow_task_no_criteria",
                               "vars": {"module": title, "task": t.get("id")}, "module_id": m["id"]})
        for item in [*m.get("tasks", []), *m.get("quiz", [])]:
            chunk_id = (item.get("source_reference") or {}).get("chunk_id")
            if chunk_id and chunk_id not in taught:
                issues.append({"severity": "error", "key": "flow_untaught_item",
                               "vars": {"module": title, "item": item.get("id")}, "module_id": m["id"]})
        code = m.get("doc_code")
        if code:
            if code in seen_docs:
                issues.append({"severity": "warning", "key": "flow_duplicate_doc", "vars": {"doc": code}, "module_id": m["id"]})
            seen_docs.add(code)

    # Company foundations (handbook, company-wide policy) must come before department practice.
    first_specific = next(((m, si) for m, si in modules if m.get("kind") != "assessment" and (m.get("tier") or 0) >= 3), None)
    if first_specific:
        for m, si in modules:
            if m.get("kind") != "assessment" and (m.get("tier") if m.get("tier") is not None else 99) <= 1 and si > first_specific[1]:
                issues.append({"severity": "warning", "key": "flow_foundation_late",
                               "vars": {"module": m.get("titleEn") or m.get("title")}, "module_id": m["id"]})

    assessments = [si for m, si in modules if m.get("kind") == "assessment"]
    if not assessments:
        issues.append({"severity": "warning", "key": "flow_no_final_assessment"})
    elif any(si != len(stages) - 1 for si in assessments):
        issues.append({"severity": "warning", "key": "flow_assessment_not_last"})
    return issues


def _taught_chunks(module: dict) -> set[str]:
    return {cid for lesson in module.get("lessons", [])
            for cid in [*(lesson.get("source_chunks") or []), (lesson.get("source_reference") or {}).get("chunk_id")] if cid}


def check_injection(stages: list[dict]) -> list[dict]:
    pseudo = []
    for e in iter_items(stages):
        item = e["item"]
        if e["kind"] == "lesson":
            text = f"{item.get('title', '')}\n{item.get('content', '')}"
        elif e["kind"] == "task":
            text = f"{item.get('title', '')}\n{item.get('completion_criteria') or ''}"
        else:
            text = "\n".join([item.get("question", ""), *(item.get("options") or [])])
        pseudo.append({"chunk_id": e["id"], "page": (e["source_reference"] or {}).get("page"), "content": text})
    return scan_chunks(pseudo)


def _coverage_score(coverage: dict | None) -> float | None:
    score = coverage.get("score") if isinstance(coverage, dict) else None
    return float(score) if isinstance(score, (int, float)) and 0 <= score <= 1 else None


def run_checks(path: LearningPath, docs: list[_Doc], chunks_by_doc: dict[str, list[dict]],
               mandatory_missing: list[str] | None = None) -> CheckResult:
    """`mandatory_missing`: mandatory matrix documents that are not among the path's sources."""
    knowledge = check_knowledge(path.stages, docs, chunks_by_doc)
    flow = check_flow(path.purpose.value, path.stages)
    injection = check_injection(path.stages)
    duplicates = check_duplicates(path.stages)
    score = _coverage_score(path.coverage)

    critical = sum(1 for k in knowledge if k["status"] in CRITICAL_KNOWLEDGE)
    warn_knowledge = sum(1 for k in knowledge if k["status"] in WARNING_KNOWLEDGE)
    flow_errors = sum(1 for f in flow if f["severity"] == "error")
    flow_warnings = sum(1 for f in flow if f["severity"] == "warning")

    blocking, manual, warnings = [], [], []
    if critical:
        blocking.append({"key": "reason_knowledge_critical", "vars": {"n": critical}})
    if injection:
        blocking.append({"key": "reason_injection_content", "vars": {"n": len(injection)}})
    if flow_errors:
        blocking.append({"key": "reason_flow_errors", "vars": {"n": flow_errors}})
    # No Pipeline 2 result yet: does not block, but the path cannot count as fully verified.
    if isinstance(path.coverage, dict) and (path.coverage.get("counts") or {}).get("required") == 0:
        # The role has no mandatory requirement in the matrix, so nothing proves the path is complete.
        manual.append({"key": "reason_matrix_empty"})
    elif score is None:
        warnings.append({"key": "reason_coverage_pending"})
    elif score < COVERAGE_MANUAL_BELOW:
        manual.append({"key": "reason_low_coverage", "vars": {"score": round(score * 100), "min": round(COVERAGE_MANUAL_BELOW * 100)}})
    elif score < COVERAGE_WARNING_BELOW:
        warnings.append({"key": "reason_medium_coverage", "vars": {"score": round(score * 100), "min": round(COVERAGE_WARNING_BELOW * 100)}})
    if warn_knowledge:
        warnings.append({"key": "reason_knowledge_warning", "vars": {"n": warn_knowledge}})
    if flow_warnings:
        warnings.append({"key": "reason_flow_warnings", "vars": {"n": flow_warnings}})
    if duplicates:
        warnings.append({"key": "reason_duplicates_found", "vars": {"n": len(duplicates)}})
    if path.excluded_chunks:
        warnings.append({"key": "reason_excluded_chunks", "vars": {"n": len(path.excluded_chunks)}})
    if mandatory_missing:
        # Not blocking: the document may not exist yet. The Reviewer decides, and must give a reason to publish.
        manual.append({"key": "reason_mandatory_sources_missing", "vars": {"codes": ", ".join(mandatory_missing)}})

    if blocking or manual:
        final, reasons = FinalStatus.MANUAL_REVIEW, [*blocking, *manual, *warnings]
    elif warnings:
        final, reasons = FinalStatus.VERIFIED_WARNING, warnings
    else:
        final, reasons = FinalStatus.VERIFIED, [{"key": "reason_all_verified"}]
    return CheckResult(knowledge, flow, injection, score, final, bool(blocking), reasons, list(mandatory_missing or []), duplicates)


def check_path(db: Session, path: LearningPath) -> CheckResult:
    """Load the documents the path cites (all versions of their codes, for lifecycle) and run every check."""
    refs = [e["source_reference"] or {} for e in iter_items(path.stages)]
    ids = {r.get("doc_id") for r in refs if r.get("doc_id")}
    codes = {r.get("doc") for r in refs if r.get("doc")}
    rows = db.scalars(select(Document).where(Document.id.in_(ids) | Document.code.in_(codes))).all()
    families = db.scalars(select(Document).where(Document.family.in_({d.family for d in rows}))).all() if rows else []
    lifecycle = compute_lifecycle(list(families), date.today())
    docs = [_Doc(d.id, d.code, lifecycle.get(d.id, ("active", None))[0]) for d in rows]

    chunks_by_doc: dict[str, list[dict]] = {}
    for c in db.scalars(select(DocumentChunk).where(DocumentChunk.document_id.in_([d.id for d in rows]))):
        chunks_by_doc.setdefault(c.document_id, []).append({"page": c.page, "norm": normalize_for_match(c.content)})
    omitted, unavailable = role_matrix.missing_mandatory_sources(db, path.target_job_position_id,
                                                                  {s.document_id for s in path.sources})
    return run_checks(path, docs, chunks_by_doc, sorted({*omitted, *unavailable}))


def check_duplicates(stages: list[dict], threshold: float = 0.85) -> list[dict]:
    """Detect near-duplicate quiz questions and tasks across modules/stages (SRS Step 35).

    Skips "assessment" modules: the final assessment is built by design to recap one question from
    every earlier module verbatim (see local_draft.py::final_quiz), so it is always a near-duplicate
    of that module's own quiz — flagging that would mark every generated path as duplicated.
    """
    quiz_items = []
    task_items = []

    for stage in stages:
        for m in stage.get("modules", []):
            if m.get("kind") == "assessment":
                continue
            for q in m.get("quiz", []):
                q_id = q.get("id")
                q_text = (q.get("question") or "").strip()
                if q_id and q_text:
                    quiz_items.append((q_id, q_text))
            for t in m.get("tasks", []):
                t_id = t.get("id")
                t_text = (t.get("title") or "").strip()
                if t_id and t_text:
                    task_items.append((t_id, t_text))

    duplicates = []
    for kind, items in (("quiz", quiz_items), ("task", task_items)):
        for i in range(len(items)):
            for j in range(i + 1, len(items)):
                id_a, text_a = items[i]
                id_b, text_b = items[j]
                norm_a = re.sub(r"\s+", " ", text_a.lower().strip())
                norm_b = re.sub(r"\s+", " ", text_b.lower().strip())
                sim = difflib.SequenceMatcher(None, norm_a, norm_b).ratio()
                if sim >= threshold:
                    duplicates.append({
                        "kind": kind,
                        "item_id_a": id_a,
                        "item_id_b": id_b,
                        "similarity": round(sim, 3),
                    })
    return duplicates
