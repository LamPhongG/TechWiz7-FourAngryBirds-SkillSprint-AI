"""Reports for HR, Reviewers and Admins (SRS Step 51-53, 62).

Every figure comes from stored data or from the checks the Reviewer sees (`path_checks.check_path`). Nothing is
estimated: without data a value is `None`, so the page can say "no data" instead of showing a made-up number
(SRS 1.8 #12 forbids fabricated validation scores).
"""
import csv
import io
from collections import defaultdict
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.comparator.engine import compare_path_with_ground_truth
from app.models import (
    Document,
    DocumentChunk,
    Enrollment,
    InjectionFlag,
    JobPosition,
    LearningPath,
    PathSource,
    PathStatus,
    QuizAttempt,
)
from app.rule_pipeline.weak_areas import analyze_weak_areas
from app.services import path_checks, role_matrix
from app.services.documents import compute_lifecycle
from app.services.progress import PASS_RATIO

# Paths whose content a Reviewer has seen or will see; drafts change too often to report on.
_REPORTED_STATUSES = (PathStatus.IN_REVIEW, PathStatus.CHANGES_REQUESTED, PathStatus.PUBLISHED)


# path id → (key, result). Three reports need the same checks; running them once per path keeps the page under a
# second instead of re-reading every cited chunk three times.
_CHECK_CACHE: dict[str, tuple[tuple, path_checks.CheckResult]] = {}


def _checks(db: Session, path: LearningPath) -> path_checks.CheckResult:
    """Checks depend on the path content and on the documents (versions, chunks), so both are part of the key."""
    key = (path.updated_at, path.revision, db.scalar(select(func.max(Document.processed_at))),
           db.scalar(select(func.count(Document.id))))
    cached = _CHECK_CACHE.get(path.id)
    if cached is None or cached[0] != key:
        cached = (key, path_checks.check_path(db, path))
        _CHECK_CACHE[path.id] = cached
    return cached[1]


def _percent(part: int, whole: int) -> int | None:
    return round(part / whole * 100) if whole else None


def _traceability(checks: path_checks.CheckResult) -> int | None:
    return _percent(sum(1 for k in checks.knowledge if k["status"] == "verified"), len(checks.knowledge))


def _latest_published(db: Session) -> dict[str, LearningPath]:
    """Job position id → its most recently published path."""
    latest: dict[str, LearningPath] = {}
    for path in db.scalars(select(LearningPath).where(LearningPath.status == PathStatus.PUBLISHED)
                           .order_by(LearningPath.published_at)):
        if path.target_job_position_id:
            latest[path.target_job_position_id] = path
    return latest


def role_coverage(db: Session) -> list[dict]:
    latest = _latest_published(db)
    rows = []
    for pos in db.scalars(select(JobPosition).order_by(JobPosition.id)):
        path = latest.get(pos.id)
        row = {"role_id": pos.id, "role_name": pos.name, "role_name_en": pos.name_en, "department": pos.department_code,
               "mandatory_requirements": sum(1 for r in role_matrix.requirements_for(db, pos.id)
                                             if r.mandatory and r.source_doc_code),
               "path_id": None, "path_title": None, "path_title_en": None, "covered_requirements": None,
               "coverage_score": None, "traceability_score": None, "final_status": None}
        if path is not None:
            topics = role_matrix.compute_coverage(db, path.stages, pos.id)["topics"]
            covered = sum(1 for t in topics if t["covered"])
            checks = _checks(db, path)
            row |= {"path_id": path.id, "path_title": path.title, "path_title_en": path.title_en,
                    "covered_requirements": covered, "coverage_score": _percent(covered, len(topics)),
                    "traceability_score": _traceability(checks), "final_status": checks.final_status.value}
        rows.append(row)
    return rows


def quiz_analytics(db: Session) -> list[dict]:
    paths = db.scalars(select(LearningPath).where(LearningPath.status == PathStatus.PUBLISHED)
                       .order_by(LearningPath.published_at)).all()
    attempts_by_path: dict[str, list[QuizAttempt]] = defaultdict(list)
    rows_q = db.execute(select(Enrollment.path_id, QuizAttempt).join(Enrollment, Enrollment.id == QuizAttempt.enrollment_id)
                        .where(Enrollment.path_id.in_([p.id for p in paths])))
    for path_id, attempt in rows_q:
        attempts_by_path[path_id].append(attempt)

    rows = []
    for path in paths:
        attempts = attempts_by_path[path.id]
        weak = {w["module_id"] for w in analyze_weak_areas(attempts, path.stages)["weak_areas"]}
        for stage in path.stages:
            for module in stage.get("modules", []):
                if not module.get("quiz"):
                    continue
                mine = [a for a in attempts if a.module_id == module["id"] and a.total]
                passed = sum(1 for a in mine if a.score / a.total >= PASS_RATIO)
                avg = round(sum(a.score / a.total for a in mine) / len(mine) * 100) if mine else None
                rows.append({
                    "path_id": path.id, "path_title": path.title, "path_title_en": path.title_en,
                    "stage_key": stage.get("key", ""), "module_id": module["id"],
                    "module_title": module.get("title") or "", "module_title_en": module.get("titleEn") or "",
                    "quiz_count": len(module["quiz"]), "attempts": len(mine),
                    "pass_rate": _percent(passed, len(mine)), "avg_score": avg,
                    "status": "no_attempts" if not mine else "weak" if module["id"] in weak else "ok",
                })
    return rows


def documents_report(db: Session) -> list[dict]:
    docs = db.scalars(select(Document).order_by(Document.code, Document.version)).all()
    lifecycle = compute_lifecycle(list(docs), date.today())
    chunk_counts = dict(db.execute(select(DocumentChunk.document_id, func.count()).group_by(DocumentChunk.document_id)).all())
    path_counts = dict(db.execute(select(PathSource.document_id, func.count(func.distinct(PathSource.path_id)))
                                  .where(PathSource.document_id.is_not(None))
                                  .group_by(PathSource.document_id)).all())

    cited: dict[str, int] = defaultdict(int)
    verified: dict[str, int] = defaultdict(int)
    for path in db.scalars(select(LearningPath).where(LearningPath.status.in_(_REPORTED_STATUSES))):
        status_by_item = {k["id"]: k["status"] for k in _checks(db, path).knowledge}
        for entry in path_checks.iter_items(path.stages):
            doc_id = (entry["source_reference"] or {}).get("doc_id")
            if doc_id:
                cited[doc_id] += 1
                verified[doc_id] += status_by_item.get(entry["id"]) == "verified"

    return [{
        "id": d.id, "code": d.code, "title": d.title, "title_en": d.title_en, "category": d.category,
        "version": d.version, "lifecycle": lifecycle[d.id][0], "processing_status": d.processing_status.value,
        "chunks_count": chunk_counts.get(d.id, 0), "referenced_in_paths": path_counts.get(d.id, 0),
        "cited_items": cited[d.id], "citation_accuracy": _percent(verified[d.id], cited[d.id]),
    } for d in docs]


def alerts(db: Session) -> list[dict]:
    rows = []
    for flag, doc in db.execute(select(InjectionFlag, Document).join(Document, Document.id == InjectionFlag.document_id)
                                .order_by(Document.code, InjectionFlag.id)):
        rows.append({"id": f"INJ-{flag.id}", "date": doc.uploaded_at, "type": "prompt_injection",
                     "severity": flag.severity, "source": f"{doc.code} v{doc.version} · {flag.chunk_id}",
                     "details": flag.match, "path_id": None, "status": "blocked"})

    for path in db.scalars(select(LearningPath).where(LearningPath.status.in_(_REPORTED_STATUSES))
                           .order_by(LearningPath.id)):
        checks = _checks(db, path)
        counts = defaultdict(int)
        for k in checks.knowledge:
            counts[k["status"]] += 1
        # These statuses block publishing, so the path cannot reach employees until they are fixed.
        for status, kind in (("hallucination", "hallucination"), ("contradiction", "unsupported_answer")):
            if counts[status]:
                rows.append({"id": f"{kind.upper()}-{path.id}", "date": path.updated_at, "type": kind, "severity": "high",
                             "source": path.id, "details": str(counts[status]), "path_id": path.id, "status": "open"})
        if path.excluded_chunks:
            rows.append({"id": f"EXCL-{path.id}", "date": path.updated_at, "type": "excluded_chunks", "severity": "medium",
                         "source": path.id, "details": str(len(path.excluded_chunks)), "path_id": path.id,
                         "status": "blocked"})
    return rows


def _reported_paths(db: Session) -> list[LearningPath]:
    return list(db.scalars(select(LearningPath).where(LearningPath.status.in_(_REPORTED_STATUSES)).order_by(LearningPath.id)))


def comparison_summary(db: Session) -> list[dict]:
    """One row per reviewed or published path: the GenAI / Python comparison totals (SRS Step 46-47)."""
    rows = []
    for path in _reported_paths(db):
        report = compare_path_with_ground_truth(db, path)
        s = report["summary"]
        rows.append({"path_id": path.id, "path_title": path.title, "path_title_en": path.title_en,
                     "role": report["role_name"], "department": path.target_department_code, "status": path.status.value,
                     "engine": path.engine, "genai_claims_available": report["genai_claims_available"],
                     "requirements": s["total_rows"], "matches": s["matches"], "mismatches": s["mismatches"] + s["outdated"],
                     "missing": s["missing"], "unsupported": s["unsupported"] + s["source_missing"] + s["contradictions"],
                     "coverage_score": report["coverage_score"], "traceability_score": report["source_traceability_score"],
                     "consistency_score": report["requirement_consistency_score"],
                     "decision": report["final_verification_status"]})
    return rows


COMPARISON_CSV_HEADERS = ("Path ID", "Requirement ID", "Role", "Source", "Python expected requirement", "Mandatory",
                          "Expected stage", "GenAI result", "Actual stage", "Match/Mismatch", "Coverage status",
                          "Traceability status", "Validation status", "Explanation of disagreement")


def comparison_csv(db: Session) -> str:
    """Requirement-level comparison of every reviewed or published path (SRS Deliverable 6)."""
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(COMPARISON_CSV_HEADERS)
    for path in _reported_paths(db):
        for r in compare_path_with_ground_truth(db, path)["rows"]:
            gen = r["genai_output"]
            fields = {f["field"]: f for f in r["field_comparisons"]}
            trace = fields.get("traceability", {}).get("match")
            writer.writerow([
                path.id, r["requirement_id"], r["role"],
                f"{r['source_document']} §{r['source_section']}" if r["source_section"] else (r["source_document"] or ""),
                r["python_ground_truth"]["text"] or "", "Yes" if r["mandatory"] else "No",
                " / ".join(r["expected_stage"]), f"{sum(1 for i in gen['items'] if i['kind'] == 'lesson')} lesson(s), "
                f"{sum(1 for i in gen['items'] if i['kind'] != 'lesson')} task/quiz item(s)",
                r["actual_stage"] or "", r["result"],
                "assessed" if gen["assessed"] and gen["taught"] else "taught" if gen["taught"] else "missing",
                "no data" if trace is None else "verified" if trace else "unverified",
                r["validation_status"], r["explanation"] or "",
            ])
    return out.getvalue()
