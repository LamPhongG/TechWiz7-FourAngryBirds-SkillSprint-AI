"""Coverage Score (SRS Steps 10, 28-30), computed from the team's real Role Requirement Matrix
(role_matrix/role_matrix.csv, imported into the RoleRequirement table by app.services.role_matrix).

Independent of what Pipeline 1 (GenAI) or the client claims — see compute_coverage()'s own docstring.

Uses its own JobPosition + RoleRequirement rows (see tests/test_path_requirements.py::position/_require)
rather than the real seeded CSV data, so these tests don't depend on (or risk polluting, in the
shared session-scoped test database) the actual role_matrix/role_matrix.csv content or codes.
"""
import uuid

from app.models import JobPosition, Priority, RoleRequirement
from app.services.role_matrix import cited_codes, compute_coverage
from tests.factories import unique_code, upload_ready_pdf


def _position(db) -> JobPosition:
    pos = JobPosition(id=f"qa-{uuid.uuid4().hex[:8]}", name="Kiểm thử viên", name_en="QA Tester", department_code="Engineering")
    db.add(pos)
    db.commit()
    return pos


def _require(db, position: JobPosition, code: str, *, mandatory: bool = True, section: str | None = "2") -> str:
    req_id = f"R9{uuid.uuid4().int % 10**6:06d}"
    db.add(RoleRequirement(id=req_id, job_position_id=position.id, process_requirement=f"Follow {code} {section}",
                           mandatory=mandatory, priority=Priority.HIGH, source_doc_code=code, source_section=section,
                           source_version="1.0", role_specific=True))
    db.commit()
    return req_id


def _stages(*citations: tuple[str, str | None]) -> list[dict]:
    """One lesson per (doc code, section heading) citation."""
    lessons = [{"id": f"L{i}", "source_reference": {"doc": code, "section": section}}
               for i, (code, section) in enumerate(citations)]
    return [{"key": "day1", "modules": [{"id": "M1", "lessons": lessons, "tasks": [], "quiz": []}]}]


def test_cited_codes_reads_every_source_reference_doc():
    assert cited_codes(_stages(("DOC-01", "1. Scope"), ("DOC-02", None))) == {"DOC-01", "DOC-02"}


def test_cited_codes_ignores_items_without_a_reference():
    stages = [{"key": "day1", "modules": [{"id": "M1", "lessons": [{"id": "L1"}], "tasks": [], "quiz": []}]}]
    assert cited_codes(stages) == set()


def test_position_without_mandatory_requirements_has_no_score(db):
    # An empty matrix proves nothing, so it must not read as 100% coverage.
    pos = _position(db)
    _require(db, pos, unique_code(), mandatory=False)
    result = compute_coverage(db, [], pos.id)
    assert result["score"] is None and result["counts"]["required"] == 0 and result["topics"] == []


def test_srs_example_three_mandatory_requirements_two_covered(db):
    """SRS 1.2: the matrix holds three mandatory requirements, the plan covers two; the missing one is reported."""
    pos = _position(db)
    code = unique_code()
    covered_a, covered_b, missing = (_require(db, pos, code, section=s) for s in ("2", "3", "4"))
    result = compute_coverage(db, _stages((code, "2 Annual leave"), (code, "3.1 Sick leave")), pos.id)
    assert result["score"] == 2 / 3
    assert result["missing"] == [missing]
    assert {t["id"] for t in result["topics"] if t["covered"]} == {covered_a, covered_b}
    assert result["counts"] == {"required": 3, "covered": 2, "missing": 1, "not_assessed": 2, "duplicate": 0,
                                "unmatched_items": 0}


def test_citing_the_document_is_not_enough_the_section_must_match(db):
    pos = _position(db)
    code = unique_code()
    _require(db, pos, code, section="4.2")
    assert compute_coverage(db, _stages((code, "4.3 Another rule")), pos.id)["score"] == 0.0
    # A citation without a section number cannot prove a specific section was taught.
    assert compute_coverage(db, _stages((code, "Introduction")), pos.id)["score"] == 0.0
    assert compute_coverage(db, _stages((code, "4.2.1 Details")), pos.id)["score"] == 1.0


def test_requirement_on_the_whole_document_is_covered_by_any_lesson_of_it(db):
    pos = _position(db)
    code = unique_code()
    _require(db, pos, code, section=None)
    assert compute_coverage(db, _stages((code, "Introduction")), pos.id)["score"] == 1.0


def test_optional_requirements_do_not_count(db):
    pos = _position(db)
    code = unique_code()
    _require(db, pos, code, section="2")
    _require(db, pos, code, mandatory=False, section="9")
    result = compute_coverage(db, _stages((code, "2 Rules")), pos.id)
    assert result["score"] == 1.0 and result["counts"]["required"] == 1


def test_stored_requirement_ids_are_ignored(db):
    # Pipeline 2 re-derives coverage from citations; ids written on items (by the model or by hand) do not count.
    pos = _position(db)
    code = unique_code()
    req_id = _require(db, pos, code, section="5")
    stages = _stages((code, "1 Other"))
    stages[0]["modules"][0]["lessons"][0]["requirement_ids"] = [req_id]
    assert compute_coverage(db, stages, pos.id)["score"] == 0.0


def test_document_level_view_still_reports_cited_documents(client, hr_headers, db):
    pos = _position(db)
    code = unique_code()
    _require(db, pos, code)
    upload_ready_pdf(client, hr_headers, code=code, category="SOP", department_code=pos.department_code)
    assert compute_coverage(db, _stages((code, "2 Annual leave")), pos.id)["requiredDocs"] == [{"code": code, "covered": True}]
    assert compute_coverage(db, [], pos.id)["requiredDocs"] == [{"code": code, "covered": False}]


def test_recompute_command_restores_coverage_from_content(client, hr_headers, db):
    from app.db import recompute_coverage
    from app.models import LearningPath
    from tests.factories import mandatory_source_ids, path_content

    doc = upload_ready_pdf(client, hr_headers)
    chunks = client.get(f"/api/documents/{doc['id']}/chunks", headers=hr_headers).json()["chunks"]
    created = client.post("/api/paths", headers=hr_headers, json={
        "job_position_id": "support-engineer", "level": "Beginner", "purpose": "onboarding",
        "source_document_ids": [doc["id"], *mandatory_source_ids(client, hr_headers, "support-engineer")],
        "content": path_content(doc, chunks)}).json()
    path = db.get(LearningPath, created["id"])
    path.coverage = None
    db.commit()

    changes = dict((pid, new) for pid, _old, new in recompute_coverage.run())
    db.expire_all()
    assert db.get(LearningPath, created["id"]).coverage["score"] == changes[created["id"]]
    assert db.get(LearningPath, created["id"]).coverage == created["coverage"]

