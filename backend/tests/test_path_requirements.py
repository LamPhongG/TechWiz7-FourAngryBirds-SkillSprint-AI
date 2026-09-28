"""HR's generation screen rules: mandatory matrix documents (SRS Step 10, 28), onboarding length (Step 13), and
tasks that carry completion criteria and a source."""
import uuid

import pytest

from app.genai_pipeline import local_draft
from app.genai_pipeline.types import GenerationRequest
from app.models import JobPosition, Priority, RoleRequirement
from app.services import paths as path_service
from tests.factories import make_pdf, path_content, policy_text, unique_code, upload, upload_ready_pdf
from tests.fake_llm import FakeLLM


@pytest.fixture
def position(db):
    """A position of its own, so its matrix rows never touch the seeded positions other tests use."""
    pos = JobPosition(id=f"qa-{uuid.uuid4().hex[:8]}", name="Kiểm thử viên", name_en="QA Tester", department_code="Engineering")
    db.add(pos)
    db.commit()
    return pos


def _require(db, position, code, *, mandatory=True, version="1.0", section="2"):
    req_id = f"R9{uuid.uuid4().int % 10**6:06d}"
    db.add(RoleRequirement(id=req_id, job_position_id=position.id, process_requirement=f"Follow {code} §{section}",
                           mandatory=mandatory, priority=Priority.HIGH, source_doc_code=code, source_section=section,
                           source_version=version, role_specific=True))
    db.commit()
    return req_id


def _create(client, headers, position, doc_ids, **extra):
    return client.post("/api/paths", headers=headers, json={
        "job_position_id": position.id, "level": "Beginner", "purpose": "onboarding", "source_document_ids": doc_ids,
    } | extra)


def _required(client, headers, position):
    res = client.get(f"/api/job-positions/{position.id}/required-sources", headers=headers)
    assert res.status_code == 200, res.text
    return {s["code"]: s for s in res.json()}


# Mandatory documents


def test_required_sources_resolve_each_code_to_the_version_in_force(client, hr_headers, db, position):
    code, optional_code, absent_code = unique_code(), unique_code(), unique_code()
    old = upload_ready_pdf(client, hr_headers, code=code, title_en=f"Policy {code}", version="1.0")
    new = upload_ready_pdf(client, hr_headers, code=code, title_en=f"Policy {code}", version="1.1")
    upload_ready_pdf(client, hr_headers, code=optional_code, title_en=f"Policy {optional_code}")
    stale = _require(db, position, code, version="1.0")
    current = _require(db, position, code, version="1.1")
    _require(db, position, optional_code, mandatory=False)
    absent = _require(db, position, absent_code)

    required = _required(client, hr_headers, position)

    assert list(required) == sorted([code, absent_code]) + [optional_code]  # mandatory first
    assert required[code]["status"] == "ready"
    assert required[code]["document"]["id"] == new["id"] != old["id"]
    assert required[code]["outdated_requirement_ids"] == [stale]
    assert current in required[code]["mandatory_requirement_ids"]
    assert required[optional_code]["mandatory"] is False
    assert required[absent_code] | {"requirement_ids": None} == {
        "code": absent_code, "mandatory": True, "status": "missing", "document": None, "requirement_ids": None,
        "mandatory_requirement_ids": [absent], "outdated_requirement_ids": []}


def test_required_sources_are_for_staff_only(client, employee_headers, position):
    assert client.get(f"/api/job-positions/{position.id}/required-sources", headers=employee_headers).status_code == 403


def test_leaving_out_a_ready_mandatory_document_is_refused(client, hr_headers, db, position):
    code = unique_code()
    mandatory = upload_ready_pdf(client, hr_headers, code=code, title_en=f"Policy {code}")
    extra = upload_ready_pdf(client, hr_headers)
    _require(db, position, code)

    refused = _create(client, hr_headers, position, [extra["id"]])
    accepted = _create(client, hr_headers, position, [extra["id"], mandatory["id"]])

    assert (refused.status_code, refused.json()["code"], refused.json()["vars"]) == (
        422, "err_mandatory_sources", {"codes": code})
    assert accepted.status_code == 201, accepted.text
    assert {s["code"] for s in accepted.json()["sources"]} == {code, extra["code"]}


def test_hr_may_leave_out_a_mandatory_document_when_confirmed(client, hr_headers, db, position):
    code = unique_code()
    upload_ready_pdf(client, hr_headers, code=code, title_en=f"Policy {code}")
    extra = upload_ready_pdf(client, hr_headers)
    _require(db, position, code)

    res = _create(client, hr_headers, position, [extra["id"]], allow_missing_mandatory=True)

    assert res.status_code == 201, res.text
    path = res.json()
    assert path["generation"]["mandatory_omitted"] == [code]
    assert "mandatory_unavailable" not in path["generation"]
    checks = client.get(f"/api/paths/{path['id']}/checks", headers=hr_headers).json()
    assert {"key": "reason_mandatory_sources_missing", "vars": {"codes": code}} in checks["reasons"]
    assert checks["final_status"] != "verified"
    log = client.get("/api/audit-logs", headers=hr_headers, params={"path_id": path["id"]}).json()["items"]
    assert log[0]["details"]["mandatory_omitted"] == code

    # Regenerating keeps HR's decision only when it is confirmed again.
    same = {"source_document_ids": [extra["id"]]}
    refused = client.post(f"/api/paths/{path['id']}/regenerate", headers=hr_headers, json=same)
    kept = client.post(f"/api/paths/{path['id']}/regenerate", headers=hr_headers, json=same | {"allow_missing_mandatory": True})
    assert (refused.status_code, refused.json()["code"]) == (422, "err_mandatory_sources")
    assert kept.status_code == 200, kept.text
    assert kept.json()["generation"]["mandatory_omitted"] == [code]


def test_an_outdated_version_does_not_satisfy_a_mandatory_document(client, hr_headers, db, position):
    code = unique_code()
    old = upload_ready_pdf(client, hr_headers, code=code, title_en=f"Policy {code}", version="1.0")
    upload_ready_pdf(client, hr_headers, code=code, title_en=f"Policy {code}", version="2.0")
    _require(db, position, code)

    res = _create(client, hr_headers, position, [old["id"]])

    assert (res.status_code, res.json()["code"]) == (422, "err_mandatory_sources")


def test_mandatory_document_not_in_repository_is_reported_not_blocking(client, hr_headers, db, position):
    absent = unique_code()
    _require(db, position, absent)
    doc = upload_ready_pdf(client, hr_headers)

    res = _create(client, hr_headers, position, [doc["id"]])

    assert res.status_code == 201, res.text
    path = res.json()
    assert path["generation"]["mandatory_unavailable"] == [absent]
    checks = client.get(f"/api/paths/{path['id']}/checks", headers=hr_headers).json()
    assert checks["mandatory_missing"] == [absent]
    assert {"key": "reason_mandatory_sources_missing", "vars": {"codes": absent}} in checks["reasons"]
    assert checks["final_status"] != "verified"


def test_regenerate_enforces_mandatory_documents_too(client, hr_headers, db, position):
    doc = upload_ready_pdf(client, hr_headers)
    draft = _create(client, hr_headers, position, [doc["id"]]).json()
    code = unique_code()
    upload_ready_pdf(client, hr_headers, code=code, title_en=f"Policy {code}")
    _require(db, position, code)

    res = client.post(f"/api/paths/{draft['id']}/regenerate", headers=hr_headers, json={"source_document_ids": [doc["id"]]})

    assert (res.status_code, res.json()["code"]) == (422, "err_mandatory_sources")
    # The document arrived after generation: the existing draft now shows the gap to the Reviewer.
    assert client.get(f"/api/paths/{draft['id']}/checks", headers=hr_headers).json()["mandatory_missing"] == [code]


# Onboarding length


def _sop(client, headers):
    """An SOP is department practice: on the 90-day template it lands on day 30, the final assessment on day 90."""
    res = upload(client, headers, make_pdf(policy_text("Deployment SOP")), "sop.pdf", category="SOP",
                 department_code="Engineering")
    assert res.status_code == 201, res.text
    return res.json()


@pytest.mark.parametrize(("days", "stages"), [(7, ["week1"]), (30, ["day30"]), (90, ["day30", "day90"])])
def test_duration_limits_the_stages(client, hr_headers, position, days, stages):
    sop = _sop(client, hr_headers)

    res = _create(client, hr_headers, position, [sop["id"]], duration_days=days)

    assert res.status_code == 201, res.text
    path = res.json()
    assert path["duration_days"] == days
    assert [s["key"] for s in path["stages"]] == stages
    assert path["generation"]["duration_days"] == days
    assert path["stages"][-1]["modules"][-1]["kind"] == "assessment"


def test_edit_cannot_move_a_module_past_the_chosen_duration(client, hr_headers, position):
    sop = _sop(client, hr_headers)
    path = _create(client, hr_headers, position, [sop["id"]], duration_days=7).json()
    moved = [{"key": "day30", "modules": path["stages"][0]["modules"]}]

    res = client.patch(f"/api/paths/{path['id']}", headers=hr_headers, json={"stages": moved})

    assert (res.status_code, res.json()["code"], res.json()["vars"]["allowed"]) == (422, "err_stage_key", "day1, week1")


def test_duration_is_ignored_for_phase_based_promotion(client, hr_headers, position):
    sop = _sop(client, hr_headers)

    res = _create(client, hr_headers, position, [sop["id"]], purpose="promotion", duration_days=7)

    assert res.status_code == 201, res.text
    assert res.json()["duration_days"] is None
    assert [s["key"] for s in res.json()["stages"]] == ["deep", "assessment"]


def test_regenerate_keeps_the_duration(client, hr_headers, position):
    sop = _sop(client, hr_headers)
    path = _create(client, hr_headers, position, [sop["id"]], duration_days=30).json()

    res = client.post(f"/api/paths/{path['id']}/regenerate", headers=hr_headers, json={"source_document_ids": [sop["id"]]})

    assert [s["key"] for s in res.json()["stages"]] == ["day30"]


def test_invalid_duration_is_rejected(client, hr_headers, position):
    sop = _sop(client, hr_headers)

    assert _create(client, hr_headers, position, [sop["id"]], duration_days=14).status_code == 422


@pytest.mark.parametrize(("days", "expected"), [
    (7, {"H": "day1", "P": "week1", "R": "week1", "S1": "week1", "S4": "week1"}),
    (30, {"H": "day1", "P": "week1", "R": "week2", "S1": "day30", "S4": "day30"}),
    (90, {"H": "day1", "P": "week1", "R": "week2", "S1": "day30", "S4": "day60"}),
])
def test_later_milestones_fold_into_the_last_stage(days, expected):
    tiers = {"H": 0, "P": 1, "R": 2, "S1": 3, "S2": 3, "S3": 3, "S4": 3}
    req = GenerationRequest(path_id="LP", purpose="onboarding", level="Beginner", role_name="", role_name_en="",
                            department="", prompt_version="v1.1", duration_days=days)

    plan = local_draft.plan_stages(req, [{"id": k, "tier": t} for k, t in tiers.items()])

    assert {k: plan[k] for k in expected} == expected


# Tasks: completion criteria and source


@pytest.fixture
def fake_gemini(monkeypatch):
    llm = FakeLLM()
    monkeypatch.setattr(path_service, "get_llm_client", lambda: llm)
    return llm


def test_rule_based_tasks_carry_criteria_and_source(client, hr_headers, position):
    doc = upload_ready_pdf(client, hr_headers)

    path = _create(client, hr_headers, position, [doc["id"]]).json()

    tasks = [t for s in path["stages"] for m in s["modules"] for t in m["tasks"]]
    assert tasks
    for task in tasks:
        assert task["completion_criteria"] and task["completion_criteriaEn"]
        assert task["source_reference"]["exact_quote"] in task["title"]
    checks = client.get(f"/api/paths/{path['id']}/checks", headers=hr_headers).json()
    assert not [f for f in checks["flow"] if f["key"] == "flow_task_no_criteria"]


def test_ai_tasks_need_criteria_backed_by_the_chunk(client, hr_headers, position, fake_gemini):
    good, missing, invented = (upload_ready_pdf(client, hr_headers) for _ in range(3))
    fake_gemini.no_criteria_docs.add(missing["code"])
    fake_gemini.invented_deadline_docs.add(invented["code"])

    path = _create(client, hr_headers, position, [good["id"], missing["id"], invented["id"]], duration_days=7).json()

    report = {m["doc"]: m for m in path["generation"]["modules"]}
    assert report[good["code"]]["tasks"] >= 1
    assert report[missing["code"]]["dropped"]["task_no_criteria"] >= 1
    assert report[invented["code"]]["dropped"]["task_criteria_unsupported"] >= 1
    tasks = [t for s in path["stages"] for m in s["modules"] if m["doc_code"] == good["code"] for t in m["tasks"]]
    assert all(t["completion_criteria"] and t["source_reference"]["exact_quote"] for t in tasks)
    # The model is told the path length and when the module is studied.
    prompt = next(c["prompt"] for c in fake_gemini.calls if c["doc"] == good["code"] and c["schema"] == "ModuleDraft")
    assert "7-day onboarding path" in prompt and "during week 1" in prompt
    assert "A task without completion criteria is rejected" in prompt


def test_python_validation_blocks_a_task_without_criteria(client, hr_headers, reviewer_headers, position):
    doc = upload_ready_pdf(client, hr_headers)
    chunks = client.get(f"/api/documents/{doc['id']}/chunks", headers=hr_headers).json()["chunks"]
    content = path_content(doc, chunks)
    del content["stages"][0]["modules"][0]["tasks"][0]["completion_criteria"]
    path = _create(client, hr_headers, position, [doc["id"]], content=content).json()

    checks = client.get(f"/api/paths/{path['id']}/checks", headers=hr_headers).json()

    assert checks["blocking"] is True
    assert [f["key"] for f in checks["flow"] if f["severity"] == "error"] == ["flow_task_no_criteria"]
    client.post(f"/api/paths/{path['id']}/submit", headers=hr_headers, json={})
    res = client.post(f"/api/paths/{path['id']}/approve", headers=reviewer_headers,
                      json={"departments": ["Engineering"], "job_positions": [], "reason": "Looks fine to me"})
    assert res.status_code == 409


def test_generation_is_briefed_with_the_positions_matrix(client, hr_headers, db, position, fake_gemini):
    code = unique_code()
    doc = upload_ready_pdf(client, hr_headers, code=code, title_en=f"Policy {code}")
    req_id = _require(db, position, code, section="2")

    path = _create(client, hr_headers, position, [doc["id"]]).json()

    prompt = next(c["prompt"] for c in fake_gemini.calls if c["doc"] == code and c["schema"] == "ModuleDraft")
    assert f"- {req_id} [Mandatory, High priority, \u00a72]" in prompt
    assert path["generation"]["requirements"]["taught"] == [req_id]
    module = next(m for s in path["stages"] for m in s["modules"] if m["doc_code"] == code)
    assert module["requirement_ids"] == [req_id]
    assert module["learning_objectives"]


def test_the_server_reads_the_file_outline_to_set_aside_other_roles_sections(client, hr_headers, position):
    from tests.factories import make_pdf, upload
    pdf = make_pdf([f"JOB DESCRIPTIONS {unique_code()}\n1. Purpose\nAll staff must read this document carefully.\n"
                    "3. Sales Executive\n3.1 Mission\nSales Executives must log every deal within 24 hours.",
                    "4. Common Rules\nEveryone must lock the screen when leaving the desk."])
    doc = upload(client, hr_headers, pdf, "jd.pdf", category="Role Description", department_code="Engineering").json()

    path = _create(client, hr_headers, position, [doc["id"]]).json()

    assert path["generation"]["off_role_sections"] == [
        {"doc": doc["code"], "section": "3", "heading": "3. Sales Executive", "chunks": 1}]
    titles = [lesson["title"] for s in path["stages"] for m in s["modules"] for lesson in m["lessons"]]
    assert "3.1 Mission" not in titles and "4. Common Rules" in titles


def test_regenerate_auto_includes_missing_documents_when_requested(client, hr_headers, db, position):
    code1 = unique_code()
    code2 = unique_code()
    doc1 = upload_ready_pdf(client, hr_headers, code=code1, title_en=f"Policy {code1}")
    doc2 = upload_ready_pdf(client, hr_headers, code=code2, title_en=f"Policy {code2}")
    _require(db, position, code1, section="1")
    _require(db, position, code2, section="1")

    # Initially HR omits doc2
    initial = _create(client, hr_headers, position, [doc1["id"]], allow_missing_mandatory=True).json()
    assert initial["generation"]["mandatory_omitted"] == [code2]
    assert initial["coverage"]["score"] < 1.0

    # HR regenerates with auto_include_missing=True
    regenerated = client.post(
        f"/api/paths/{initial['id']}/regenerate",
        headers=hr_headers,
        json={"source_document_ids": [doc1["id"]], "auto_include_missing": True},
    ).json()

    # doc2 was automatically included from approved repository
    source_codes = {s["code"] for s in regenerated["sources"]}
    assert code1 in source_codes
    assert code2 in source_codes

    # Python validation pipeline independently evaluated the result and achieved 100% coverage
    assert regenerated["coverage"]["score"] == 1.0
    assert len(regenerated["coverage"]["missing"]) == 0

