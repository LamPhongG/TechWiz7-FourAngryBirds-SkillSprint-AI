"""GenAI / Python comparison per requirement (SRS Step 46-47, Table 1). Every Match comes from real data."""
import uuid

import pytest
from sqlalchemy import delete, select

from app.comparator.engine import compare_path_with_ground_truth
from app.models import JobPosition, LearningPath, PathLevel, PathPurpose, PathStatus, Priority, RoleRequirement, User
from app.rule_pipeline.requirements import section_number
from tests.factories import unique_code, upload_ready_pdf


def _requirement(db, position_id: str, code: str, section: str, *, mandatory: bool = True,
                 assessment: str | None = None) -> str:
    rid = f"R8{uuid.uuid4().int % 10**6:06d}"
    db.add(RoleRequirement(id=rid, job_position_id=position_id, process_requirement=f"Rule {section}",
                           mandatory=mandatory, priority=Priority.HIGH, source_doc_code=code, source_section=section,
                           source_version="1.0", role_specific=True, assessment_requirement=assessment))
    return rid


def _ref(doc: dict, chunk: dict) -> dict:
    return {"doc_id": doc["id"], "doc": doc["code"], "section": chunk["heading"], "page": chunk["page"],
            "chunk_id": chunk["chunk_id"], "exact_quote": chunk["content"][:60]}


@pytest.fixture
def temp_position(db):
    """A position of its own, removed afterwards: test_database counts positions in the shared session database."""
    pos = JobPosition(id=f"cmp-{uuid.uuid4().hex[:8]}", name="Đối chiếu", name_en="Comparison Tester",
                      department_code="Engineering")
    db.add(pos)
    db.commit()
    yield pos
    db.rollback()
    db.execute(delete(LearningPath).where(LearningPath.target_job_position_id == pos.id))
    db.execute(delete(RoleRequirement).where(RoleRequirement.job_position_id == pos.id))
    db.execute(delete(JobPosition).where(JobPosition.id == pos.id))
    db.commit()


def test_comparison_reports_real_matches_mismatches_and_gaps(client, hr_headers, db, temp_position):
    pos = temp_position
    code = unique_code()
    doc = upload_ready_pdf(client, hr_headers, code=code, category="SOP", department_code="Engineering")
    chunks = [c for c in client.get(f"/api/documents/{doc['id']}/chunks", headers=hr_headers).json()["chunks"]
              if section_number(c["heading"])]
    first, second = chunks[0], chunks[1]
    matched = _requirement(db, pos.id, code, section_number(first["heading"]), assessment="Quiz on the rule")
    wrong_stage = _requirement(db, pos.id, code, section_number(second["heading"]))
    missing = _requirement(db, pos.id, code, "9")
    optional = _requirement(db, pos.id, code, "8", mandatory=False)

    quote = first["content"][:60]
    lesson_a = {"id": "CMP-M1-L1", "title": "A", "content": first["content"], "minutes": 1, "source_reference": _ref(doc, first),
                # What the model declared (Pipeline 1 schema v1.2): one real requirement and one the matrix lacks.
                "genai_claims": {"requirement_ids": [matched, "R-NOT-IN-MATRIX"]}}
    question = {"id": "CMP-M1-Q1", "kind": "ai", "question": "Which is correct?", "options": ["Zebra", max(quote.split(), key=len), "Quokka"],
                "answer": 1, "source_reference": _ref(doc, first)}
    lesson_b = {"id": "CMP-M2-L1", "title": "B", "content": second["content"], "minutes": 1, "source_reference": _ref(doc, second)}
    hr_id = db.scalar(select(User.id).where(User.email == "hr@fourangrybirds.vn"))
    path = LearningPath(
        id=f"LP-CMP-{uuid.uuid4().hex[:6]}", title="So sánh", title_en="Comparison", purpose=PathPurpose.ONBOARDING,
        level=PathLevel.BEGINNER, status=PathStatus.IN_REVIEW, created_by_id=hr_id, target_job_position_id=pos.id,
        target_department_code="Engineering", engine="gemini", prompt_version="v1.2", duration_days=90,
        stages=[
            # An SOP is expected on day 30 or day 60, so the module placed on day 1 is a stage mismatch.
            {"key": "day1", "modules": [{"id": "CMP-M2", "title": "B", "doc_code": code, "lessons": [lesson_b],
                                         "tasks": [], "quiz": []}]},
            {"key": "day30", "modules": [{"id": "CMP-M1", "title": "A", "doc_code": code, "lessons": [lesson_a],
                                          "tasks": [], "quiz": [question]}]},
        ])
    db.add(path)
    db.commit()

    report = compare_path_with_ground_truth(db, path)
    rows = {r["requirement_id"]: r for r in report["rows"]}

    assert rows[matched]["result"] == "Match"
    assert all(f["match"] is True for f in rows[matched]["field_comparisons"])
    assert rows[wrong_stage]["result"] == "Mismatch" and "due_stage" in rows[wrong_stage]["failed_fields"]
    assert rows[wrong_stage]["actual_stage"] == "day1" and rows[wrong_stage]["expected_stage"] == ["day30", "day60"]
    assert rows[missing]["result"] == "Missing Requirement" and rows[missing]["validation_status"] == "Incomplete"
    # Nothing to compare for a requirement that was never taught: no field may claim a match.
    assert all(f["match"] is not True for f in rows[missing]["field_comparisons"])
    assert rows[optional]["result"] == "Not Covered (Optional)"
    assert rows["R-NOT-IN-MATRIX"]["result"] == "Unsupported Requirement"

    assert (report["summary"]["matches"], report["summary"]["mismatches"], report["summary"]["missing"],
            report["summary"]["unsupported"]) == (1, 1, 1, 1)
    assert report["coverage_score"] == round(2 / 3 * 100)
    assert report["requirement_consistency_score"] == 50
    assert report["final_verification_status"] == "Unsupported"
    assert report["genai_claims_available"] is True

    res = client.get(f"/api/paths/{path.id}/comparison", headers=hr_headers)
    assert res.status_code == 200 and res.json()["summary"]["total_rows"] == 5


def test_rule_based_draft_has_no_genai_claims_to_compare(client, hr_headers, db):
    report_path = db.scalar(select(LearningPath).where(LearningPath.engine == "local-draft").limit(1))
    if report_path is None:
        return
    report = compare_path_with_ground_truth(db, report_path)
    assert report["genai_claims_available"] is False
    assert all(f["match"] is None for r in report["rows"] for f in r["field_comparisons"] if f["field"] == "genai_claim")
