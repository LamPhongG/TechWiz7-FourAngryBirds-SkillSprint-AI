import copy

import pytest
from sqlalchemy import select

from app.db.base import new_id
from app.models import LearningPath, PathAssignment, PathStatus, User, UserRole
from app.services import enrollments
from tests.factories import mandatory_source_ids, path_content, upload_ready_pdf


@pytest.fixture
def source(client, hr_headers):
    doc = upload_ready_pdf(client, hr_headers)
    chunks = client.get(f"/api/documents/{doc['id']}/chunks", headers=hr_headers).json()["chunks"]
    return doc, chunks


@pytest.fixture
def create_body(client, hr_headers, source):
    doc, chunks = source
    return {
        "job_position_id": "support-engineer",
        "level": "Intermediate",
        "purpose": "onboarding",
        "source_document_ids": [doc["id"], *mandatory_source_ids(client, hr_headers, "support-engineer")],
        "prompt": "  Focus on customer escalation  ",
        "content": path_content(doc, chunks),
    }


@pytest.fixture
def draft(client, hr_headers, create_body):
    res = client.post("/api/paths", headers=hr_headers, json=create_body)
    assert res.status_code == 201, res.text
    return res.json()


def _set_status(db, path_id: str, status: PathStatus, departments=(), positions=()):
    """Moves a path without the approve checks; publishing assigns it the way `approve` does."""
    path = db.get(LearningPath, path_id)
    path.status = status
    for dept in departments:
        path.assignments.append(PathAssignment(department_code=dept))
    for pos in positions:
        path.assignments.append(PathAssignment(job_position_id=pos))
    if status is PathStatus.PUBLISHED:
        reviewer = db.scalar(select(User).where(User.user_role == UserRole.REVIEWER))
        enrollments.assign_published_path(db, path, reviewer)
    db.commit()


def _audit(client, headers, path_id):
    return client.get("/api/audit-logs", headers=headers, params={"path_id": path_id}).json()["items"]


def test_hr_creates_a_draft(client, hr_headers, draft, source):
    doc, _ = source

    assert draft["id"].startswith("LP-")
    assert draft["status"] == "draft"
    assert draft["revision"] == 1
    assert draft["title"] == "Onboarding — Software Support Engineer"
    assert draft["title_en"] == "Onboarding — Software Support Engineer"
    assert draft["target"] == {"job_position_id": "support-engineer", "department_code": "Engineering"}
    assert draft["prompt"] == "Focus on customer escalation"
    # Mandatory matrix documents that earlier tests uploaded follow the one HR picked.
    assert draft["sources"][0] == {"document_id": doc["id"], "code": doc["code"], "version": "1.0",
                                   "title": doc["title"], "title_en": doc["title_en"]}
    assert draft["duration_days"] == 90
    assert draft["module_count"] == 1
    assert draft["created_by"]["name"] == "Jordan Lee"
    assert set(draft["allowed_actions"]) == {"edit", "regenerate", "submit", "delete", "comment"}
    # Extra generator fields survive the round trip
    assert draft["stages"][0]["modules"][0]["titleEn"] == doc["title_en"]

    log = _audit(client, hr_headers, draft["id"])
    assert [(e["action"], e["status_after"]) for e in log] == [("generate", "draft")]
    assert log[0]["details"]["sources"].split(", ")[0] == doc["code"]


@pytest.mark.parametrize(
    ("mutate", "status", "code"),
    [
        (lambda b: b["content"]["stages"][0].update(key="deep"), 422, "err_stage_key"),
        (lambda b: b.update(job_position_id="astronaut"), 422, "err_job_position"),
        (lambda b: b.update(source_document_ids=["DV-NOPE"]), 422, "err_source_missing"),
    ],
)
def test_create_rejects_invalid_input(client, hr_headers, create_body, mutate, status, code):
    body = copy.deepcopy(create_body)
    mutate(body)

    res = client.post("/api/paths", headers=hr_headers, json=body)

    assert res.status_code == status
    assert res.json()["code"] == code


def test_create_validates_content_tree(client, hr_headers, create_body):
    duplicate = copy.deepcopy(create_body)
    module = duplicate["content"]["stages"][0]["modules"][0]
    module["tasks"][0]["id"] = module["lessons"][0]["id"]
    bad_answer = copy.deepcopy(create_body)
    bad_answer["content"]["stages"][0]["modules"][0]["quiz"][0]["answer"] = 7

    assert client.post("/api/paths", headers=hr_headers, json=duplicate).status_code == 422
    assert client.post("/api/paths", headers=hr_headers, json=bad_answer).status_code == 422


def test_unprocessed_source_is_refused(client, hr_headers, create_body):
    from tests.factories import make_scanned_pdf, upload
    failed = upload(client, hr_headers, make_scanned_pdf(), "scan.pdf").json()
    create_body["source_document_ids"] = [failed["id"]]

    res = client.post("/api/paths", headers=hr_headers, json=create_body)

    assert (res.status_code, res.json()["code"]) == (409, "err_source_not_ready")


def test_only_hr_creates_paths(client, reviewer_headers, employee_headers, create_body):
    assert client.post("/api/paths", headers=reviewer_headers, json=create_body).status_code == 403
    assert client.post("/api/paths", headers=employee_headers, json=create_body).status_code == 403


def test_drafts_are_hidden_from_reviewers_and_employees(client, reviewer_headers, employee_headers, draft):
    assert client.get(f"/api/paths/{draft['id']}", headers=reviewer_headers).status_code == 404
    assert draft["id"] not in {p["id"] for p in client.get("/api/paths", headers=reviewer_headers).json()}
    assert client.get(f"/api/paths/{draft['id']}", headers=employee_headers).status_code == 404


def test_hr_edits_draft_content(client, hr_headers, draft):
    stages = draft["stages"]
    stages[0]["modules"][0]["lessons"][0]["title"] = "Scope (edited)"

    res = client.patch(f"/api/paths/{draft['id']}", headers=hr_headers,
                       json={"stages": stages, "details": {"item": stages[0]["modules"][0]["lessons"][0]["id"]}})

    assert res.status_code == 200
    assert res.json()["stages"][0]["modules"][0]["lessons"][0]["title"] == "Scope (edited)"
    assert _audit(client, hr_headers, draft["id"])[0]["action"] == "edit"


def test_regenerate_replaces_content_and_sources(client, hr_headers, draft):
    new_doc = upload_ready_pdf(client, hr_headers)
    chunks = client.get(f"/api/documents/{new_doc['id']}/chunks", headers=hr_headers).json()["chunks"]

    res = client.post(f"/api/paths/{draft['id']}/regenerate", headers=hr_headers, json={
        "source_document_ids": [new_doc["id"], *mandatory_source_ids(client, hr_headers, "support-engineer")],
        "content": path_content(new_doc, chunks, prefix="LP-R2") | {"engine": "gemini"},
    })

    assert res.status_code == 200
    body = res.json()
    assert body["sources"][0]["code"] == new_doc["code"]
    assert draft["sources"][0]["code"] not in {s["code"] for s in body["sources"]}
    assert body["engine"] == "gemini"
    assert body["prompt"] == "Focus on customer escalation"
    assert body["stages"][0]["modules"][0]["id"] == "LP-R2-M1"


def test_submit_moves_to_review_with_note(client, hr_headers, reviewer_headers, draft):
    # Add a mandatory Engineering document that is not cited, then "edit" back the exact
    # old content so Pipeline 2 recomputes coverage — ensures coverage < 100% deterministically.
    upload_ready_pdf(client, hr_headers, category="SOP", department_code="Engineering")
    client.patch(f"/api/paths/{draft['id']}", headers=hr_headers, json={"stages": draft["stages"]})

    res = client.post(f"/api/paths/{draft['id']}/submit", headers=hr_headers,
                      json={"note": "Please check stage 1", "final_status": "verified_warning"})

    assert res.status_code == 200
    path = res.json()
    assert path["status"] == "in_review"
    assert path["revision"] == 1
    assert path["comments"][0]["text"] == "Please check stage 1"
    assert path["comments"][0]["author"]["role"] == "hr"
    assert set(path["allowed_actions"]) == {"comment"}

    # Result is server's judgment (coverage from Pipeline 2 below 100%), not the client-supplied value.
    log = _audit(client, reviewer_headers, draft["id"])[0]
    assert (log["action"], log["status_before"], log["status_after"], log["final_status"]) == (
        "submit", "draft", "in_review", "manual_review")
    assert client.get(f"/api/paths/{draft['id']}", headers=reviewer_headers).status_code == 200


def test_hr_cannot_edit_while_in_review_but_reviewer_can(client, hr_headers, reviewer_headers, draft):
    client.post(f"/api/paths/{draft['id']}/submit", headers=hr_headers, json={})

    blocked = client.patch(f"/api/paths/{draft['id']}", headers=hr_headers, json={"stages": draft["stages"]})
    reviewer_edit = client.patch(f"/api/paths/{draft['id']}", headers=reviewer_headers, json={"stages": draft["stages"]})

    assert (blocked.status_code, blocked.json()["code"]) == (409, "err_action_not_allowed")
    assert reviewer_edit.status_code == 200


def test_resubmit_after_changes_requested_bumps_revision(client, db, hr_headers, draft):
    client.post(f"/api/paths/{draft['id']}/submit", headers=hr_headers, json={})
    _set_status(db, draft["id"], PathStatus.CHANGES_REQUESTED)

    res = client.post(f"/api/paths/{draft['id']}/submit", headers=hr_headers, json={})

    assert res.json()["status"] == "in_review"
    assert res.json()["revision"] == 2
    assert _audit(client, hr_headers, draft["id"])[0]["action"] == "resubmit"


def test_only_drafts_can_be_deleted_and_history_is_kept(client, hr_headers, create_body):
    draft = client.post("/api/paths", headers=hr_headers, json=create_body).json()
    submitted = client.post("/api/paths", headers=hr_headers, json=create_body).json()
    client.post(f"/api/paths/{submitted['id']}/submit", headers=hr_headers, json={})

    assert client.delete(f"/api/paths/{submitted['id']}", headers=hr_headers).status_code == 409
    assert client.delete(f"/api/paths/{draft['id']}", headers=hr_headers).status_code == 204
    assert client.get(f"/api/paths/{draft['id']}", headers=hr_headers).status_code == 404
    assert [e["action"] for e in _audit(client, hr_headers, draft["id"])] == ["delete", "generate"]


def test_published_path_reaches_employee_and_can_be_archived(client, db, hr_headers, employee_headers, draft):
    client.post(f"/api/paths/{draft['id']}/submit", headers=hr_headers, json={})
    _set_status(db, draft["id"], PathStatus.PUBLISHED, departments=["Engineering"])

    employee_view = client.get("/api/paths", headers=employee_headers).json()
    assert draft["id"] in {p["id"] for p in employee_view}
    assert client.get(f"/api/paths/{draft['id']}", headers=employee_headers).json()["published_to"] == {
        "departments": ["Engineering"], "job_positions": []}

    short = client.post(f"/api/paths/{draft['id']}/archive", headers=hr_headers, json={"reason": "old"})
    assert short.status_code == 422
    res = client.post(f"/api/paths/{draft['id']}/archive", headers=hr_headers,
                      json={"reason": "Policy DOC-03 replaced by v2.0"})
    assert res.json()["status"] == "archived"
    assert res.json()["archived_at"] is not None
    assert draft["id"] not in {p["id"] for p in client.get("/api/paths", headers=employee_headers).json()}
    assert _audit(client, hr_headers, draft["id"])[0]["reason"] == "Policy DOC-03 replaced by v2.0"


def test_path_published_to_a_position_only_reaches_that_position(client, db, hr_headers, employee_headers, draft):
    client.post(f"/api/paths/{draft['id']}/submit", headers=hr_headers, json={})
    _set_status(db, draft["id"], PathStatus.PUBLISHED, positions=["sales-exec"])

    assert client.get(f"/api/paths/{draft['id']}", headers=employee_headers).status_code == 404


def test_comments_threads_and_resolution(client, db, hr_headers, reviewer_headers, employee_headers, draft):
    lesson = draft["stages"][0]["modules"][0]["lessons"][0]
    client.post(f"/api/paths/{draft['id']}/submit", headers=hr_headers, json={})

    first = client.post(f"/api/paths/{draft['id']}/comments", headers=reviewer_headers,
                        json={"text": "Quote does not match the source", "item_ref": {"id": lesson["id"], "label": "L1"}})
    assert first.status_code == 201
    comment = first.json()["comments"][-1]
    assert comment["item_ref"] == {"id": lesson["id"], "label": "L1"}

    reply = client.post(f"/api/paths/{draft['id']}/comments", headers=hr_headers,
                        json={"text": "Fixed in r2", "reply_to": comment["id"]})
    assert reply.json()["comments"][-1]["reply_to"] == comment["id"]
    bad_reply = client.post(f"/api/paths/{draft['id']}/comments", headers=hr_headers,
                            json={"text": "?", "reply_to": "CMT-NOPE"})
    assert bad_reply.status_code == 422
    assert client.post(f"/api/paths/{draft['id']}/comments", headers=hr_headers, json={"text": "   "}).status_code == 422

    resolved = client.post(f"/api/paths/{draft['id']}/comments/{comment['id']}/resolve", headers=hr_headers, json={})
    stored = next(c for c in resolved.json()["comments"] if c["id"] == comment["id"])
    assert stored["resolved"] is True
    assert stored["resolved_by"]["name"] == "Jordan Lee"
    assert resolved.json()["open_comment_count"] == 1

    _set_status(db, draft["id"], PathStatus.PUBLISHED, departments=["Company-wide"])
    denied = client.post(f"/api/paths/{draft['id']}/comments", headers=employee_headers, json={"text": "Hi"})
    assert denied.status_code == 403


def test_list_filters_by_status(client, hr_headers, create_body):
    submitted = client.post("/api/paths", headers=hr_headers, json=create_body).json()
    client.post(f"/api/paths/{submitted['id']}/submit", headers=hr_headers, json={})

    in_review = client.get("/api/paths", headers=hr_headers, params={"status": "in_review"}).json()

    assert submitted["id"] in {p["id"] for p in in_review}
    assert all(p["status"] == "in_review" for p in in_review)
    assert "stages" not in in_review[0]


def test_audit_log_access_and_paging(client, hr_headers, employee_headers, draft):
    assert client.get("/api/audit-logs", headers=employee_headers).status_code == 403

    page = client.get("/api/audit-logs", headers=hr_headers, params={"limit": 1, "action": "generate"}).json()

    assert len(page["items"]) == 1
    assert page["total"] >= 1
    assert page["items"][0]["action"] == "generate"


def test_timestamps_read_from_the_database_are_utc(client, db, hr_headers, draft):
    # A fresh request reads created_at back from SQLite, which stores no offset.
    db.expire_all()
    fetched = client.get(f"/api/paths/{draft['id']}", headers=hr_headers).json()

    assert fetched["created_at"].endswith(("Z", "+00:00"))
    assert fetched["created_at"][:16] == draft["created_at"][:16]


def test_unknown_path_is_404(client, hr_headers):
    res = client.get(f"/api/paths/{new_id('LP')}", headers=hr_headers)
    assert (res.status_code, res.json()["code"]) == (404, "err_path_not_found")
