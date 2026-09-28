"""GenAI / Python comparison per requirement (SRS Step 46-47, Table 1, Deliverable 6). No AI SDK.

For every Role Requirement Matrix row of the path's role, what Pipeline 1 produced is compared with what Pipeline 2
expects. A field is compared only when both sides have independent data; otherwise `match` is `None` ("no data"),
never a default "Match" (SRS 1.8 #12 forbids hard-coded comparison results).

Fields:
- coverage: a lesson cites the requirement's document and section (expected when the requirement is mandatory);
- due_stage: stage of the first module teaching it, against the stage the document's tier leads to;
- assessment: a task or question on it, when the matrix names an assessment requirement;
- traceability: every item on it has a quote found verbatim in the source (knowledge check "verified");
- source_version: version of the cited document against the matrix's Source_Version;
- genai_claim: the requirement id the model declared for its items (`item["genai_claims"]`, Pipeline 1 schema v1.2);
  paths written before that schema, or by the rule-based draft, have no claim to compare.
"""
from types import SimpleNamespace
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.genai_pipeline.local_draft import assign_stage
from app.genai_pipeline.types import doc_tier, stage_template
from app.ingestion.validation import normalize_version
from app.models import Document, JobPosition, LearningPath
from app.rule_pipeline.coverage import evaluate_requirements
from app.rule_pipeline.requirements import module_items, section_number
from app.services import path_checks
from app.services.role_matrix import as_generation_dict, required_sources, requirements_for

FIELDS = ("coverage", "due_stage", "assessment", "traceability", "source_version", "genai_claim")


def _expected_stages(purpose: str, duration: int | None, document: Document | None) -> list[str]:
    """Stages the rule-based planner would give this document's module; SOPs may fall on day 30 or day 60."""
    if document is None:
        return []
    template = stage_template(purpose, duration)
    tier = doc_tier(SimpleNamespace(category=document.category, department=document.department_code))
    keys = {assign_stage(purpose, tier, 0), assign_stage(purpose, tier, 99)}
    return sorted({k if k in template else template[-1] for k in keys}, key=template.index)


def _covers(req: dict, doc_code: str | None, section: str | None) -> bool:
    """Same rule as `rule_pipeline.coverage`: a citation without a section only covers whole-document requirements."""
    if not doc_code or req["source_doc_code"] != doc_code:
        return False
    wanted = req["source_section"]
    return wanted is None or (section is not None and (section == wanted or section.startswith(wanted + ".")))


def _field(name: str, genai: Any, python: Any, match: bool | None) -> dict:
    return {"field": name, "genai": genai, "gt": python, "match": match}


def compare_path_with_ground_truth(db: Session, path: LearningPath) -> dict[str, Any]:
    role_id = path.target_job_position_id
    position = db.get(JobPosition, role_id) if role_id else None
    role_name = position.name_en if position else (role_id or "")
    reqs = [as_generation_dict(r) for r in requirements_for(db, role_id) if r.source_doc_code] if role_id else []
    documents = {e["code"]: e.get("document") for e in required_sources(db, role_id)} if role_id else {}
    knowledge = {k["id"]: k["status"] for k in path_checks.check_path(db, path).knowledge}
    cited_ids = {(e["source_reference"] or {}).get("doc_id") for e in path_checks.iter_items(path.stages)} - {None}
    versions = {d.id: d.version for d in db.scalars(select(Document).where(Document.id.in_(cited_ids)))}
    evaluation = evaluate_requirements(path.stages, reqs)

    # What Pipeline 1 produced for each requirement, and what the model itself declared.
    items_by_req: dict[str, list[dict]] = {r["id"]: [] for r in reqs}
    claimed: dict[str, int] = {}
    claims_available = False
    for stage in path.stages:
        for module in stage.get("modules", []):
            if module.get("kind") == "assessment":
                continue
            for kind, item in module_items(module):
                ref = item.get("source_reference") or {}
                doc_code, section = ref.get("doc") or module.get("doc_code"), section_number(ref.get("section"))
                for req in reqs:
                    if _covers(req, doc_code, section):
                        items_by_req[req["id"]].append({"kind": kind, "id": item.get("id"), "stage": stage.get("key"),
                                                        "module": module.get("title"), "section": ref.get("section"),
                                                        "version": versions.get(ref.get("doc_id"))})
                claims = item.get("genai_claims")
                if isinstance(claims, dict):
                    claims_available = True
                    for rid in claims.get("requirement_ids") or []:
                        claimed[rid] = claimed.get(rid, 0) + 1

    rows = []
    for req in reqs:
        items = items_by_req[req["id"]]
        lessons = [i for i in items if i["kind"] == "lesson"]
        taught, assessed = bool(lessons), any(i["kind"] != "lesson" for i in items)
        expected = _expected_stages(path.purpose.value, path.duration_days, documents.get(req["source_doc_code"]))
        actual_stage = lessons[0]["stage"] if lessons else None
        statuses = [knowledge.get(i["id"]) for i in items]
        cited_versions = sorted({i["version"] for i in items if i["version"]})
        wanted_version = normalize_version(req["source_version"]) if req.get("source_version") else None
        fields = [
            _field("coverage", len(lessons), "mandatory" if req["mandatory"] else "optional",
                   taught if req["mandatory"] else None),
            _field("due_stage", actual_stage, expected or None,
                   (actual_stage in expected) if taught and expected else None),
            _field("assessment", assessed, req.get("assessment"),
                   assessed if taught and req.get("assessment") else None),
            _field("traceability", f"{statuses.count('verified')}/{len(statuses)}" if statuses else None, "all",
                   all(s == "verified" for s in statuses) if statuses else None),
            _field("source_version", cited_versions or None, wanted_version,
                   all(normalize_version(v) == wanted_version for v in cited_versions)
                   if cited_versions and wanted_version else None),
            _field("genai_claim", claimed.get(req["id"], 0) if claims_available else None, req["id"],
                   (req["id"] in claimed) == taught if claims_available and taught else None),
        ]
        failed = [f["field"] for f in fields if f["match"] is False]
        if req["mandatory"] and not taught:
            result, status = "Missing Requirement", "Incomplete"
        elif "contradiction" in statuses:
            result, status = "Contradiction Detected", "Contradictory"
        elif "traceability" in failed:
            result, status = "Source Support Missing", "Unsupported"
        elif "source_version" in failed:
            result, status = "Outdated Source", "Verified with Warning"
        elif failed:
            result, status = "Mismatch", "Verified with Warning"
        elif not taught:
            result, status = "Not Covered (Optional)", "Verified"
        else:
            result, status = "Match", "Verified"
        rows.append({
            "requirement_id": req["id"], "role": role_name,
            "source_document": req["source_doc_code"], "source_section": req["source_section"],
            "mandatory": req["mandatory"], "priority": req["priority"],
            "expected_stage": expected, "actual_stage": actual_stage,
            "genai_output": {"items": items, "taught": taught, "assessed": assessed},
            "python_ground_truth": {"text": req["text"], "assessment": req.get("assessment"),
                                    "source_version": req.get("source_version")},
            "field_comparisons": fields, "failed_fields": failed,
            "result": result, "validation_status": status,
            "explanation": ("; ".join(f"{f['field']}: GenAI {f['genai']} vs expected {f['gt']}"
                                      for f in fields if f["match"] is False) or None),
        })

    # Requirement ids the model declared that the role's matrix does not contain (SRS "Unsupported Requirement").
    known = {r["id"] for r in reqs}
    for rid, n in sorted(claimed.items()):
        if rid not in known:
            rows.append({"requirement_id": rid, "role": role_name, "source_document": None, "source_section": None,
                         "mandatory": False, "priority": None, "expected_stage": [], "actual_stage": None,
                         "genai_output": {"items": [], "taught": False, "assessed": False, "claimed_items": n},
                         "python_ground_truth": {"text": None, "assessment": None, "source_version": None},
                         "field_comparisons": [_field("genai_claim", n, None, False)],
                         "failed_fields": ["genai_claim"], "result": "Unsupported Requirement",
                         "validation_status": "Unsupported",
                         "explanation": f"The model declared {rid}, which the role's matrix does not contain."})

    def count(result: str) -> int:
        return sum(1 for r in rows if r["result"] == result)

    compared = [r for r in rows if r["genai_output"]["taught"]]
    matches = count("Match")
    summary = {"matches": matches, "mismatches": count("Mismatch"), "missing": count("Missing Requirement"),
               "unsupported": count("Unsupported Requirement"), "contradictions": count("Contradiction Detected"),
               "source_missing": count("Source Support Missing"), "outdated": count("Outdated Source"),
               "optional_not_covered": count("Not Covered (Optional)"), "total_rows": len(rows),
               "unmatched_items": evaluation["unmatched_items"]}
    if summary["unsupported"] or summary["source_missing"]:
        final = "Unsupported"
    elif summary["contradictions"]:
        final = "Contradictory"
    elif summary["missing"] or evaluation["score"] is None:
        final = "Incomplete"
    elif summary["mismatches"] or summary["outdated"]:
        final = "Verified with Warning"
    else:
        final = "Verified"
    traced = list(knowledge.values())
    return {
        "path_id": path.id, "path_title": path.title, "role_id": role_id or "", "role_name": role_name,
        "engine": path.engine, "genai_claims_available": claims_available,
        "total_requirements": len(reqs), "mandatory_requirements": evaluation["required"],
        "covered_mandatory_requirements": len(evaluation["covered"]),
        "coverage_score": round(evaluation["score"] * 100) if evaluation["score"] is not None else None,
        "source_traceability_score": round(traced.count("verified") / len(traced) * 100) if traced else None,
        "requirement_consistency_score": round(matches / len(compared) * 100) if compared else None,
        "final_verification_status": final, "summary": summary, "fields": list(FIELDS), "rows": rows,
    }
