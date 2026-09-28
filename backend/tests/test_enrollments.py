"""Assignment of published paths and progress (reports/Project_Report.md §5.3–§5.6).

Seeded employees: Alex (Engineering, support-engineer, onboarding not started), Minh (Engineering, team-leader,
onboarding completed in 2023), Linh (Customer Support, cs-exec, joins 28/09/2026).
"""
from datetime import date, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.db import seed
from app.models import Enrollment
from tests.conftest import login
from tests.factories import mandatory_source_ids, path_content, upload_ready_pdf

REASON = "Coverage pending from Pipeline 2"


@pytest.fixture
def minh_headers(client):
    return login(client, "minh.nguyen@fourangrybirds.vn")


@pytest.fixture
def linh_headers(client):
    return login(client, "linh.tran@fourangrybirds.vn")


def _publish(client, hr, reviewer, *, purpose="onboarding", position="support-engineer", duration=None,
             departments=(), positions=()):
    doc = upload_ready_pdf(client, hr)
    chunks = client.get(f"/api/documents/{doc['id']}/chunks", headers=hr).json()["chunks"]
    body = {"job_position_id": position, "level": "Beginner", "purpose": purpose,
            "source_document_ids": [doc["id"], *mandatory_source_ids(client, hr, position)],
            "content": path_content(doc, chunks, stage="day1" if purpose == "onboarding" else "foundation")}
    if duration:
        body["duration_days"] = duration
    created = client.post("/api/paths", headers=hr, json=body)
    assert created.status_code == 201, created.text
    path_id = created.json()["id"]
    client.post(f"/api/paths/{path_id}/submit", headers=hr, json={})
    res = client.post(f"/api/paths/{path_id}/approve", headers=reviewer,
                      json={"departments": list(departments), "job_positions": list(positions), "reason": REASON})
    assert res.status_code == 200, res.text
    return res.json()


def _mine(client, headers) -> dict[str, dict]:
    res = client.get("/api/me/enrollments", headers=headers)
    assert res.status_code == 200, res.text
    return {e["path_id"]: e for e in res.json()}


def _visible(client, headers) -> set[str]:
    return {p["id"] for p in client.get("/api/paths", headers=headers).json()}


def _learners(client, headers, path_id) -> dict[str, dict]:
    return {row["name"]: row for row in client.get(f"/api/paths/{path_id}/enrollments", headers=headers).json()}


def test_onboarding_goes_to_employees_who_have_not_finished_onboarding(
        client, hr_headers, reviewer_headers, employee_headers, minh_headers):
    path = _publish(client, hr_headers, reviewer_headers, departments=["Engineering"])

    alex = _mine(client, employee_headers)[path["id"]]
    assert (alex["status"], alex["source"], alex["progress"]["percent"]) == ("assigned", "auto_department", 0)
    assert path["id"] in _visible(client, employee_headers)
    # Decision Q1: Minh is in Engineering but finished onboarding in 2023.
    assert path["id"] not in _mine(client, minh_headers)
    assert client.get(f"/api/paths/{path['id']}", headers=minh_headers).status_code == 404
    # Every Engineering employee who has not finished onboarding gets it (the seed also has "Tech Lead"), Minh does not.
    learners = _learners(client, hr_headers, path["id"])
    assert "Alex Morgan" in learners and "Tech Lead" not in learners
    assert "Minh Nguyen" not in learners


def test_employee_matching_two_onboarding_paths_gets_both(client, hr_headers, reviewer_headers, employee_headers):
    by_department = _publish(client, hr_headers, reviewer_headers, departments=["Engineering"])
    by_position = _publish(client, hr_headers, reviewer_headers, positions=["support-engineer"])
    both_targets = _publish(client, hr_headers, reviewer_headers, departments=["Engineering"],
                            positions=["support-engineer"])

    mine = _mine(client, employee_headers)
    # Decision Q2: one record per path, so matching two paths gives both.
    assert mine[by_department["id"]]["source"] == "auto_department"
    assert mine[by_position["id"]]["source"] == "auto_position"
    # One path targeting both the department and the position is still one record.
    assert mine[both_targets["id"]]["source"] == "auto_position"
    rows = client.get(f"/api/paths/{both_targets['id']}/enrollments", headers=hr_headers).json()
    assert [r["name"] for r in rows].count("Alex Morgan") == 1


def test_company_wide_onboarding_reaches_every_new_employee(
        client, hr_headers, reviewer_headers, employee_headers, linh_headers, minh_headers):
    path = _publish(client, hr_headers, reviewer_headers, departments=["Company-wide"])

    assert path["id"] in _mine(client, employee_headers)
    assert path["id"] in _mine(client, linh_headers)
    assert path["id"] not in _mine(client, minh_headers)


def test_promotion_follows_publish_targets_until_manual_assignment_exists(
        client, hr_headers, reviewer_headers, minh_headers, employee_headers):
    path = _publish(client, hr_headers, reviewer_headers, purpose="promotion", position="team-leader",
                    positions=["team-leader"])

    minh = _mine(client, minh_headers)[path["id"]]
    assert (minh["source"], minh["due_date"]) == ("auto_position", None)
    assert path["id"] not in _mine(client, employee_headers)


def test_onboarding_due_date_counts_from_the_joining_date(client, hr_headers, reviewer_headers, linh_headers):
    path = _publish(client, hr_headers, reviewer_headers, position="cs-exec", duration=30, positions=["cs-exec"])

    today = date.today()
    expected = date(2026, 9, 28) + timedelta(days=30)
    if expected < today:
        expected = today + timedelta(days=30)
    assert _mine(client, linh_headers)[path["id"]]["due_date"] == expected.isoformat()


def test_newly_created_employee_gets_the_onboarding_path(client, hr_headers, reviewer_headers, db):
    path = _publish(client, hr_headers, reviewer_headers, position="cs-exec", positions=["cs-exec"])
    email = f"{uuid4().hex[:8]}@fourangrybirds.vn"
    created = client.post("/api/users/from-cv", headers=hr_headers,
                          json={"name": "New Hire", "email": email, "job_position_id": "cs-exec"})
    assert created.status_code == 201, created.text
    user_id = created.json()["user"]["id"]

    enrollment = db.scalar(select(Enrollment).where(Enrollment.user_id == user_id, Enrollment.path_id == path["id"]))
    assert enrollment is not None and enrollment.status == "assigned"
    log = client.get("/api/audit-logs", headers=hr_headers, params={"path_id": path["id"], "action": "assign"}).json()
    assert any(row["details"].get("employee") == email for row in log["items"])


def test_progress_moves_from_assigned_to_completed(client, hr_headers, reviewer_headers, employee_headers):
    path = _publish(client, hr_headers, reviewer_headers, positions=["support-engineer"])
    module = path["stages"][0]["modules"][0]
    base = f"/api/me/enrollments/{path['id']}"

    read = client.post(f"{base}/lessons/{module['lessons'][0]['id']}", headers=employee_headers).json()
    assert (read["status"], read["progress"]["percent"]) == ("in_progress", 0)
    assert read["started_at"] is not None

    client.put(f"{base}/tasks/{module['tasks'][0]['id']}", headers=employee_headers, json={"done": True})
    question = module["quiz"][0]
    wrong = client.post(f"{base}/quizzes/{module['id']}", headers=employee_headers,
                        json={"answers": {question["id"]: (question["answer"] + 1) % 3}}).json()
    assert (wrong["passed"], wrong["enrollment"]["status"]) == (False, "in_progress")

    right = client.post(f"{base}/quizzes/{module['id']}", headers=employee_headers,
                        json={"answers": {question["id"]: question["answer"]}}).json()
    assert (right["score"], right["total"], right["passed"]) == (1, 1, True)
    assert right["enrollment"]["status"] == "completed"
    assert right["enrollment"]["progress"] == {"done": 1, "total": 1, "percent": 100}
    assert len(right["enrollment"]["quiz"][module["id"]]) == 2

    learner = _learners(client, hr_headers, path["id"])["Alex Morgan"]
    assert (learner["status"], learner["percent"]) == ("completed", 100)


def test_progress_is_private_to_the_assigned_employee(
        client, hr_headers, reviewer_headers, employee_headers, minh_headers):
    path = _publish(client, hr_headers, reviewer_headers, positions=["support-engineer"])
    lesson = path["stages"][0]["modules"][0]["lessons"][0]["id"]

    assert client.post(f"/api/me/enrollments/{path['id']}/lessons/{lesson}", headers=minh_headers).status_code == 404
    assert client.post(f"/api/me/enrollments/{path['id']}/lessons/nope", headers=employee_headers).status_code == 404
    assert client.get("/api/me/enrollments", headers=reviewer_headers).status_code == 403
    assert client.get(f"/api/paths/{path['id']}/enrollments", headers=employee_headers).status_code == 403


def test_archiving_withdraws_learners_still_studying(client, hr_headers, reviewer_headers, employee_headers,
                                                     linh_headers):
    path = _publish(client, hr_headers, reviewer_headers, departments=["Engineering", "Customer Support"])
    module = path["stages"][0]["modules"][0]
    base = f"/api/me/enrollments/{path['id']}"
    client.post(f"{base}/lessons/{module['lessons'][0]['id']}", headers=linh_headers)
    client.put(f"{base}/tasks/{module['tasks'][0]['id']}", headers=linh_headers, json={"done": True})
    client.post(f"{base}/quizzes/{module['id']}", headers=linh_headers,
                json={"answers": {module["quiz"][0]["id"]: module["quiz"][0]["answer"]}})

    res = client.post(f"/api/paths/{path['id']}/archive", headers=hr_headers, json={"reason": "Policy replaced by v2"})
    assert res.status_code == 200, res.text

    learners = _learners(client, hr_headers, path["id"])
    assert learners["Alex Morgan"]["status"] == "withdrawn"
    assert learners["Linh Tran"]["status"] == "completed"
    assert path["id"] not in _visible(client, employee_headers)
    assert path["id"] not in _mine(client, employee_headers)


def _explore(client, headers) -> dict[str, dict]:
    res = client.get("/api/explore/paths", headers=headers)
    assert res.status_code == 200, res.text
    return {p["id"]: p for p in res.json()}


def test_explore_lists_department_paths_even_when_not_assigned(
        client, hr_headers, reviewer_headers, employee_headers, minh_headers, linh_headers):
    onboarding = _publish(client, hr_headers, reviewer_headers, departments=["Engineering"])
    leader = _publish(client, hr_headers, reviewer_headers, purpose="promotion", position="team-leader",
                      positions=["team-leader"])

    # Minh finished onboarding, so it is not assigned (Q1), but he can still browse it.
    minh = _explore(client, minh_headers)
    assert minh[onboarding["id"]]["enrollment"] is None
    assert minh[leader["id"]]["for_my_position"] is True
    # A position of Alex's department is visible to Alex, as a preview of what comes next.
    alex = _explore(client, employee_headers)
    assert alex[onboarding["id"]]["enrollment"]["status"] == "assigned"
    assert alex[leader["id"]]["for_my_position"] is False
    assert onboarding["id"] not in _explore(client, linh_headers)


def test_preview_shows_the_outline_without_answers(client, hr_headers, reviewer_headers, minh_headers):
    path = _publish(client, hr_headers, reviewer_headers, departments=["Engineering"])

    preview = client.get(f"/api/explore/paths/{path['id']}", headers=minh_headers).json()
    module = preview["outline"][0]["modules"][0]
    assert (preview["modules"], module["tasks"], module["questions"]) == (1, 1, 1)
    assert module["lessons"] == [path["stages"][0]["modules"][0]["lessons"][0]["title"]]
    assert "answer" not in str(preview) and "content" not in module


def test_employee_joins_an_optional_path_of_their_department(
        client, hr_headers, reviewer_headers, minh_headers, linh_headers):
    path = _publish(client, hr_headers, reviewer_headers, departments=["Engineering"])
    assert path["id"] not in _visible(client, minh_headers)

    joined = client.post(f"/api/explore/paths/{path['id']}/enroll", headers=minh_headers)
    assert joined.status_code == 201, joined.text
    assert (joined.json()["source"], joined.json()["due_date"], joined.json()["status"]) == ("self", None, "assigned")
    assert path["id"] in _visible(client, minh_headers)
    assert _explore(client, minh_headers)[path["id"]]["enrollment"]["source"] == "self"

    again = client.post(f"/api/explore/paths/{path['id']}/enroll", headers=minh_headers)
    other_department = client.post(f"/api/explore/paths/{path['id']}/enroll", headers=linh_headers)
    assert (again.status_code, again.json()["code"]) == (409, "err_already_enrolled")
    assert other_department.status_code == 404
    assert client.get("/api/explore/paths", headers=hr_headers).status_code == 403


def test_all_learners_endpoint(client, hr_headers, reviewer_headers, employee_headers):
    path = _publish(client, hr_headers, reviewer_headers, positions=["support-engineer"])
    res = client.get("/api/learners", headers=hr_headers)
    assert res.status_code == 200
    learners = res.json()
    assert any(l["name"] == "Alex Morgan" and l["path_id"] == path["id"] for l in learners)
    assert client.get("/api/learners", headers=employee_headers).status_code == 403
def test_demo_certificate_seed_uses_only_a_path_published_to_sales(client, hr_headers, reviewer_headers, db):
    sales_headers = login(client, "sales.emp@fourangrybirds.vn")
    elsewhere = _publish(client, hr_headers, reviewer_headers, departments=["Engineering"])
    _publish(client, hr_headers, reviewer_headers, position="sales-exec", departments=["Sales"])
    seed.run(db)

    mine = _mine(client, sales_headers)
    # A path published to another department is never borrowed for the Sales demo account.
    assert elsewhere["id"] not in mine
    completed = [r for r in mine.values() if r["status"] == "completed"]
    assert len(completed) == 1
    assert completed[0]["progress"]["percent"] == 100

    seed.run(db)
    assert _mine(client, sales_headers)[completed[0]["path_id"]]["completed_at"] == completed[0]["completed_at"]


def test_employee_department_transfer_syncs_enrollments(client, hr_headers, reviewer_headers, employee_headers):
    # 1. Publish onboarding path for Engineering and Finance
    eng_path = _publish(client, hr_headers, reviewer_headers, position="support-engineer", departments=["Engineering"])
    fin_path = _publish(client, hr_headers, reviewer_headers, position="finance-associate", departments=["Finance"])

    # 2. Alex Morgan starts in Engineering -> has eng_path, not fin_path
    me = client.get("/api/auth/me", headers=employee_headers).json()
    alex_id = me["id"]
    mine = _mine(client, employee_headers)
    assert eng_path["id"] in mine
    assert fin_path["id"] not in mine

    # 3. HR transfers Alex to Finance department
    transfer_res = client.patch(
        f"/api/users/{alex_id}",
        headers=hr_headers,
        json={"department_code": "Finance", "job_position_id": "finance-associate"},
    )
    assert transfer_res.status_code == 200

    # 4. Alex's enrollments should now have fin_path and eng_path should be withdrawn (not in _mine)
    mine_after = _mine(client, employee_headers)
    assert fin_path["id"] in mine_after
    assert eng_path["id"] not in mine_after

    # 5. Check enrollment status in explore/learners
    explore = _explore(client, employee_headers)
    assert explore[fin_path["id"]]["enrollment"]["status"] == "assigned"
    # eng_path is no longer even in explore for a Finance employee
    assert eng_path["id"] not in explore

    # 6. Transfer Alex back to Engineering -> eng_path is reopened, fin_path is withdrawn
    back_res = client.patch(
        f"/api/users/{alex_id}",
        headers=hr_headers,
        json={"department_code": "Engineering", "job_position_id": "support-engineer"},
    )
    assert back_res.status_code == 200
    mine_back = _mine(client, employee_headers)
    assert eng_path["id"] in mine_back
    assert fin_path["id"] not in mine_back

