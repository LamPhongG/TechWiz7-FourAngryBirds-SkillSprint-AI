"""Background generation jobs: the timeline state, and the API that starts and follows them."""
import time

import pytest

from app.services import generation_jobs as jobs
from app.services import paths as path_service
from tests.factories import mandatory_source_ids, path_content, upload_ready_pdf
from tests.fake_llm import FakeLLM

POSITION = "finance-associate"


def _fresh_state() -> dict:
    return jobs.Job(id="J", kind="create", actor_id="U").state


def test_events_fold_into_a_timeline():
    state = _fresh_state()
    assert state["steps"]["sources"] == "active"

    jobs.apply_event(state, "sources", {"count": 2})
    jobs.apply_event(state, "analysis", {"chunks": 9})
    jobs.apply_event(state, "plan", {"engine": "gemini", "modules": [{"id": "M1", "doc": "DOC-01"}, {"id": "M2", "doc": "DOC-07"}]})
    assert state["steps"] == {"sources": "done", "analysis": "done", "plan": "done", "modules": "active",
                              "coverage": "pending", "saving": "pending"}
    assert [m["phase"] for m in state["modules"]] == ["waiting", "waiting"]

    jobs.apply_event(state, "module", {"id": "M2", "phase": "quiz", "lessons": 3})
    jobs.apply_event(state, "module", {"id": "M1", "phase": "fallback", "error": "UPSTREAM_UNAVAILABLE"})
    assert state["modules"][1] | {} == {"id": "M2", "doc": "DOC-07", "phase": "quiz", "lessons": 3}
    assert state["modules"][0]["phase"] == "fallback"

    jobs.apply_event(state, "assemble", {})
    assert state["steps"]["modules"] == "done"
    assert state["steps"]["coverage"] == "skipped"  # no matrix for this role
    assert state["steps"]["saving"] == "active"


def test_client_supplied_content_skips_the_pipeline_steps():
    state = _fresh_state()
    jobs.apply_event(state, "sources", {"count": 1})
    jobs.apply_event(state, "saving", {})

    assert state["steps"] == {"sources": "done", "analysis": "skipped", "plan": "skipped", "modules": "skipped",
                              "coverage": "skipped", "saving": "active"}


def _wait(client, headers, job_id, timeout=20):
    deadline = time.time() + timeout
    while time.time() < deadline:
        job = client.get(f"/api/paths/jobs/{job_id}", headers=headers).json()
        if job["status"] != "running":
            return job
        time.sleep(0.05)
    raise AssertionError(f"job {job_id} still running")


@pytest.fixture
def fake_gemini(monkeypatch):
    llm = FakeLLM()
    monkeypatch.setattr(path_service, "get_llm_client", lambda: llm)
    return llm


def _body(client, headers, doc_ids, **extra):
    return {"job_position_id": POSITION, "level": "Beginner", "purpose": "onboarding",
            "source_document_ids": [*doc_ids, *mandatory_source_ids(client, headers, POSITION)]} | extra


def test_create_job_reports_every_module_and_returns_the_path(client, hr_headers, fake_gemini):
    docs = [upload_ready_pdf(client, hr_headers) for _ in range(2)]

    started = client.post("/api/paths/jobs", headers=hr_headers, json=_body(client, hr_headers, [d["id"] for d in docs]))

    assert started.status_code == 202
    assert started.json()["status"] == "running"
    job = _wait(client, hr_headers, started.json()["id"])
    assert job["status"] == "done", job
    assert job["state"]["engine"] == "gemini"
    assert set(job["state"]["steps"].values()) <= {"done", "skipped"}
    assert job["state"]["analysis"]["used_documents"] == len(job["state"]["modules"])
    assert all(m["phase"] == "done" and m["lessons"] >= 1 for m in job["state"]["modules"])
    path = client.get(f"/api/paths/{job['path_id']}", headers=hr_headers)
    assert path.status_code == 200 and path.json()["status"] == "draft"


def test_a_module_that_falls_back_is_visible_in_the_timeline(client, hr_headers, fake_gemini):
    good, broken = (upload_ready_pdf(client, hr_headers) for _ in range(2))
    fake_gemini.fail_docs.add(broken["code"])

    job = _wait(client, hr_headers, client.post("/api/paths/jobs", headers=hr_headers,
                                                json=_body(client, hr_headers, [good["id"], broken["id"]])).json()["id"])

    by_doc = {m["doc"]: m for m in job["state"]["modules"]}
    assert by_doc[broken["code"]]["phase"] == "fallback"
    assert by_doc[broken["code"]]["error"] == "UPSTREAM_UNAVAILABLE"
    assert by_doc[good["code"]]["phase"] == "done"


def test_business_errors_fail_the_job_with_a_translatable_code(client, hr_headers):
    job = _wait(client, hr_headers, client.post("/api/paths/jobs", headers=hr_headers, json={
        "job_position_id": POSITION, "level": "Beginner", "purpose": "onboarding",
        "source_document_ids": ["DV-NOPE"]}).json()["id"])

    assert job["status"] == "failed"
    assert job["error"]["code"] == "err_source_missing" and job["error"]["status"] == 422
    assert job["state"]["steps"]["sources"] == "failed"


def test_client_supplied_content_goes_through_a_job_too(client, hr_headers):
    doc = upload_ready_pdf(client, hr_headers)
    chunks = client.get(f"/api/documents/{doc['id']}/chunks", headers=hr_headers).json()["chunks"]

    job = _wait(client, hr_headers, client.post("/api/paths/jobs", headers=hr_headers,
                                                json=_body(client, hr_headers, [doc["id"]], content=path_content(doc, chunks))).json()["id"])

    assert job["status"] == "done"
    assert job["state"]["steps"]["plan"] == "skipped"


def test_regenerate_job_checks_the_path_before_starting(client, hr_headers, reviewer_headers, fake_gemini):
    doc = upload_ready_pdf(client, hr_headers)
    draft = client.post("/api/paths", headers=hr_headers, json=_body(client, hr_headers, [doc["id"]])).json()

    missing = client.post("/api/paths/LP-NOPE/regenerate/jobs", headers=hr_headers, json={"source_document_ids": [doc["id"]]})
    started = client.post(f"/api/paths/{draft['id']}/regenerate/jobs", headers=hr_headers,
                          json={"source_document_ids": _body(client, hr_headers, [doc["id"]])["source_document_ids"]})

    assert missing.status_code == 404
    job = _wait(client, hr_headers, started.json()["id"])
    assert (job["kind"], job["status"], job["path_id"]) == ("regenerate", "done", draft["id"])
    # Jobs are private to the HR user who started them; Reviewers cannot poll them at all.
    assert client.get(f"/api/paths/jobs/{job['id']}", headers=reviewer_headers).status_code == 403


def test_jobs_are_private_to_their_owner():
    class Someone:
        id = "USR-OTHER"

    job = jobs.Job(id="JOB-X", kind="create", actor_id="USR-OWNER")
    jobs._jobs[job.id] = job
    try:
        assert jobs.get("JOB-X", Someone()) is None
    finally:
        del jobs._jobs[job.id]
