"""Role Requirement Matrix (SRS Step 10): CSV import, lookups, and matching of plan items to requirements.

The CSV format is the team's `role_matrix/role_matrix.csv`:
Requirement_ID, Role, Policy_Requirement, Process_Requirement, Competency, Mandatory_Optional, Priority,
Source_Document, Source_Section, Assessment_Requirement, and the optional Source_Version and Scope
(Company-wide / Role-specific).
"""
import csv
import io
import re
from dataclasses import dataclass, field
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.ingestion.validation import VERSION_PATTERN, compare_versions, normalize_version
from app.models import Document, JobPosition, Priority, ProcessingStatus, RoleRequirement
from app.rule_pipeline.coverage import evaluate_requirements
from app.rule_pipeline.precedence import precedence_tier
from app.rule_pipeline.requirements import section_number
from app.services.documents import compute_lifecycle

REQUIRED_COLUMNS = ("Requirement_ID", "Role", "Mandatory_Optional", "Priority", "Source_Document", "Source_Section")
SCOPES = {"company-wide": False, "role-specific": True}
_EMPTY = {"", "—", "-", "n/a", "na"}
_REQ_ID = re.compile(r"^R\d{3,}$")


def normalize_role(name: str) -> str:
    """'Team Leader/Tech Lead' and 'Team Leader / Tech Lead' are the same role."""
    return re.sub(r"\s+", " ", re.sub(r"\s*/\s*", " / ", name or "")).strip().lower()


def _clean(value: str | None) -> str | None:
    value = (value or "").strip()
    return None if value.lower() in _EMPTY else value


@dataclass
class ImportReport:
    created: int = 0
    updated: int = 0
    errors: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {"created": self.created, "updated": self.updated, "errors": self.errors}


def import_csv(db: Session, text: str) -> ImportReport:
    """Upsert matrix rows by Requirement ID. Rows with errors are skipped and reported, the rest are saved.

    Raises:
        AppError: the header is missing required columns.
    """
    reader = csv.DictReader(io.StringIO(text.lstrip("﻿")))
    missing = [c for c in REQUIRED_COLUMNS if c not in (reader.fieldnames or [])]
    if missing:
        raise AppError(422, "err_matrix_columns", f"Missing columns: {', '.join(missing)}", columns=", ".join(missing))

    positions = {normalize_role(p.name_en): p.id for p in db.scalars(select(JobPosition))}
    report = ImportReport()
    for line_no, row in enumerate(reader, start=2):
        req_id = (row.get("Requirement_ID") or "").strip().upper()
        position_id = positions.get(normalize_role(row.get("Role", "")))
        kind = (row.get("Mandatory_Optional") or "").strip().lower()
        priority = (row.get("Priority") or "").strip().capitalize()
        problems = []
        if not _REQ_ID.match(req_id):
            problems.append(f"invalid Requirement_ID '{req_id}'")
        if position_id is None:
            problems.append(f"unknown role '{row.get('Role')}'")
        if kind not in ("mandatory", "optional"):
            problems.append(f"Mandatory_Optional must be Mandatory or Optional, got '{row.get('Mandatory_Optional')}'")
        if priority not in {p.value for p in Priority}:
            problems.append(f"Priority must be High, Medium or Low, got '{row.get('Priority')}'")
        # A matrix without the Scope column predates it; its rows are treated as company-wide until classified.
        scope = (_clean(row.get("Scope")) or "company-wide").lower()
        if scope not in SCOPES:
            problems.append(f"Scope must be Company-wide or Role-specific, got '{row.get('Scope')}'")
        version = _clean(row.get("Source_Version"))
        version = normalize_version(version) if version else None
        if version and not VERSION_PATTERN.match(version):
            problems.append(f"Source_Version must look like 1.0, got '{row.get('Source_Version')}'")
        if problems:
            report.errors.append(f"line {line_no}: " + "; ".join(problems))
            continue

        # "PENDING — Phase 2" and similar placeholders mean the source is not written yet.
        doc = _clean(row.get("Source_Document"))
        doc = doc.replace("SOP-", "DOC-") if doc and re.match(r"^(DOC|SOP)-\d+$", doc) else None
        values = {
            "job_position_id": position_id,
            "policy_requirement": _clean(row.get("Policy_Requirement")),
            "process_requirement": _clean(row.get("Process_Requirement")),
            "competency": _clean(row.get("Competency")),
            "mandatory": kind == "mandatory",
            "priority": Priority(priority),
            "source_doc_code": doc,
            "source_section": section_number(row.get("Source_Section")) if doc else None,
            "source_version": version if doc else None,
            "role_specific": SCOPES[scope],
            "assessment_requirement": _clean(row.get("Assessment_Requirement")),
        }
        existing = db.get(RoleRequirement, req_id)
        if existing:
            for key, value in values.items():
                setattr(existing, key, value)
            report.updated += 1
        else:
            db.add(RoleRequirement(id=req_id, **values))
            report.created += 1
    db.flush()
    return report


def requirements_for(db: Session, job_position_id: str) -> list[RoleRequirement]:
    return list(db.scalars(select(RoleRequirement).where(RoleRequirement.job_position_id == job_position_id)
                           .order_by(RoleRequirement.id)))


def requirement_text(req: RoleRequirement) -> str:
    return req.process_requirement or req.policy_requirement or req.competency or req.id


def as_generation_dict(req: RoleRequirement) -> dict:
    return {"id": req.id, "text": requirement_text(req), "competency": req.competency, "mandatory": req.mandatory,
            "priority": req.priority.value, "source_doc_code": req.source_doc_code, "source_section": req.source_section,
            "source_version": req.source_version, "role_specific": req.role_specific,
            "assessment": req.assessment_requirement}


def required_sources(db: Session, job_position_id: str, today: date | None = None) -> list[dict]:
    """Documents the matrix cites for a position, each resolved to the version in force today.

    A document is mandatory when at least one Mandatory requirement cites it. Order: mandatory first, then by code.
    """
    by_code: dict[str, dict] = {}
    for req in requirements_for(db, job_position_id):
        if not req.source_doc_code:
            continue
        entry = by_code.setdefault(req.source_doc_code, {
            "code": req.source_doc_code, "mandatory": False, "requirement_ids": [], "mandatory_requirement_ids": [],
            "outdated_requirement_ids": [], "_versions": {},
        })
        entry["requirement_ids"].append(req.id)
        entry["_versions"][req.id] = req.source_version
        if req.mandatory:
            entry["mandatory"] = True
            entry["mandatory_requirement_ids"].append(req.id)
    if not by_code:
        return []

    docs = db.scalars(select(Document).where(Document.code.in_(by_code))).all()
    # Lifecycle depends on every version of a family, including versions filed under another code (DOC-02 → DOC-01).
    family = db.scalars(select(Document).where(Document.family.in_({d.family for d in docs}))).all() if docs else []
    lifecycle = compute_lifecycle(list(family), today or date.today())
    for code, entry in by_code.items():
        active = [d for d in docs if d.code == code and lifecycle[d.id][0] == "active"]
        doc = max(active, key=_version_key, default=None)
        entry["document"] = doc
        entry["status"] = ("missing" if doc is None
                           else "ready" if doc.processing_status is ProcessingStatus.READY else "not_ready")
        versions = entry.pop("_versions")
        if doc is not None:
            entry["outdated_requirement_ids"] = [rid for rid, v in versions.items()
                                                 if v and compare_versions(v, doc.version) < 0]
    return sorted(by_code.values(), key=lambda e: (not e["mandatory"], e["code"]))


def _version_key(doc: Document):
    return [int(p) for p in normalize_version(doc.version).split(".")]


def cited_codes(stages: list[dict]) -> set[str]:
    """Every document code cited anywhere (lessons/tasks/quiz) in a generated path's stages."""
    codes: set[str] = set()
    for stage in stages:
        for module in stage.get("modules", []):
            for key in ("lessons", "tasks", "quiz"):
                for item in module.get(key, []):
                    code = (item.get("source_reference") or {}).get("doc")
                    if code:
                        codes.add(code)
    return codes


def compute_coverage(db: Session, stages: list[dict], job_position_id: str) -> dict:
    """Coverage Score (SRS Step 28-29) of a path for its role, computed by Pipeline 2 from the final content.

    `score` = covered mandatory requirements / total mandatory requirements, where a requirement is covered when a
    lesson cites its document and section (`rule_pipeline.coverage.evaluate_requirements`). `None` when the role has no
    mandatory requirement yet: an empty matrix must not look like full coverage. `requiredDocs` is the document-level
    view of the same matrix, `topics` the requirement-level one (shape shared with the frontend).
    """
    reqs = [as_generation_dict(r) for r in requirements_for(db, job_position_id) if r.source_doc_code]
    result = evaluate_requirements(stages, reqs)
    cited = cited_codes(stages)
    mandatory_docs = sorted(
        (e for e in required_sources(db, job_position_id) if e["mandatory"]),
        key=lambda e: precedence_tier(e["document"]) if e["document"] else 99,
    )
    covered, not_assessed = set(result["covered"]), set(result["not_assessed"])
    return {
        "score": result["score"],
        "requiredDocs": [{"code": e["code"], "covered": e["code"] in cited} for e in mandatory_docs],
        "topics": [{"id": r["id"], "label": r["text"], "covered": r["id"] in covered,
                    "assessed": r["id"] in covered and r["id"] not in not_assessed, "matchedKeyword": None}
                   for r in reqs if r["mandatory"]],
        "counts": {"required": result["required"], "covered": len(result["covered"]), "missing": len(result["missing"]),
                   "not_assessed": len(result["not_assessed"]), "duplicate": len(result["duplicate"]),
                   "unmatched_items": result["unmatched_items"]},
        "missing": result["missing"],
    }


def missing_mandatory_sources(db: Session, job_position_id: str, source_ids: set[str]) -> tuple[list[str], list[str]]:
    """(codes HR left out although the version in force is ready, codes that cannot be selected yet).

    The first list blocks generation. The second is not HR's omission (not uploaded, still processing, or only an
    outdated version on file), so the path is still generated and the gap is reported to the Reviewer.
    """
    omitted, unavailable = [], []
    for entry in required_sources(db, job_position_id):
        if not entry["mandatory"]:
            continue
        if entry["status"] != "ready":
            unavailable.append(entry["code"])
        elif entry["document"].id not in source_ids:
            omitted.append(entry["code"])
    return omitted, unavailable
