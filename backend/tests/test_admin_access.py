"""Admin oversight (SRS Step 51, 1.6 ii): Admins read paths, documents, progress, reports and the audit trail, but take
no part in the HR / Reviewer workflow."""
import pytest

from tests.conftest import login
from tests.factories import make_pdf, mandatory_source_ids, path_content, policy_text, upload_ready_pdf


@pytest.fixture
def admin_headers(client):
    return login(client, "admin@fourangrybirds.vn")


@pytest.fixture
def draft_path(client, hr_headers):
    doc = upload_ready_pdf(client, hr_headers)
    chunks = client.get(f"/api/documents/{doc['id']}/chunks", headers=hr_headers).json()["chunks"]
    res = client.post("/api/paths", headers=hr_headers, json={
        "job_position_id": "support-engineer", "level": "Beginner", "purpose": "onboarding",
        "source_document_ids": [doc["id"], *mandatory_source_ids(client, hr_headers, "support-engineer")],
        "content": path_content(doc, chunks)})
    assert res.status_code == 201, res.text
    return res.json()


def test_admin_reads_everything_needed_for_oversight(client, admin_headers, draft_path):
    pid = draft_path["id"]
    assert pid in {p["id"] for p in client.get("/api/paths", headers=admin_headers).json()}
    for url in (f"/api/paths/{pid}", f"/api/paths/{pid}/checks", f"/api/paths/{pid}/comparison", f"/api/paths/{pid}/enrollments",
                "/api/documents", "/api/learners", "/api/audit-logs", "/api/reports/role-coverage", "/api/reports/alerts",
                "/api/reports/comparison", "/api/users"):
        assert client.get(url, headers=admin_headers).status_code == 200, url
    assert client.get("/api/documents", headers=admin_headers).json()
    # A read-only view: the server offers the Admin no workflow action on the path.
    assert client.get(f"/api/paths/{pid}", headers=admin_headers).json()["allowed_actions"] == []


def test_admin_cannot_act_in_the_workflow(client, admin_headers, draft_path):
    pid = draft_path["id"]
    doc = {"code": "DOC-97", "title_en": "Admin upload", "category": "FAQ", "department_code": "Company-wide",
           "version": "1.0", "effective_date": "2026-01-01"}
    assert client.post("/api/documents", headers=admin_headers, data=doc,
                       files={"file": ("a.pdf", make_pdf(policy_text()))}).status_code == 403
    assert client.post(f"/api/paths/{pid}/submit", headers=admin_headers, json={}).status_code == 403
    assert client.post(f"/api/paths/{pid}/approve", headers=admin_headers,
                       json={"departments": ["Engineering"], "reason": "Admin should not approve"}).status_code == 403
    assert client.post(f"/api/paths/{pid}/comments", headers=admin_headers, json={"text": "Admin comment"}).status_code == 403
