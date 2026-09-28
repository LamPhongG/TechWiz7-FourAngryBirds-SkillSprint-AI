"""User management access (SRS 1.6 ii, Deliverable 9 unauthorized-access tests)."""
import uuid

import pytest

from tests.conftest import login


@pytest.fixture
def admin_headers(client):
    return login(client, "admin@fourangrybirds.vn")


def _new_user(role: str) -> dict:
    return {"email": f"u.{uuid.uuid4().hex[:8]}@fourangrybirds.vn", "name": "Test User", "password": "Temp@1234",
            "user_role": role, "department_code": "Sales", "job_position_id": "sales-exec" if role == "employee" else None}


def test_employees_and_reviewers_cannot_read_accounts(client, employee_headers, reviewer_headers):
    for headers in (employee_headers, reviewer_headers):
        assert client.get("/api/users", headers=headers).status_code == 403
        me = client.get("/api/auth/me", headers=headers).json()
        assert client.get(f"/api/users/{me['id']}", headers=headers).status_code == 403


def test_hr_manages_employees_only(client, hr_headers, admin_headers):
    assert client.get("/api/users", headers=hr_headers).status_code == 200
    # An HR account must not be able to create or promote staff accounts (privilege escalation).
    assert client.post("/api/users", headers=hr_headers, json=_new_user("admin")).status_code == 403
    assert client.post("/api/users", headers=hr_headers, json=_new_user("reviewer")).status_code == 403
    employee = client.post("/api/users", headers=hr_headers, json=_new_user("employee"))
    assert employee.status_code == 201
    uid = employee.json()["id"]
    assert client.patch(f"/api/users/{uid}", headers=hr_headers, json={"user_role": "admin"}).status_code == 403
    assert client.patch(f"/api/users/{uid}", headers=hr_headers, json={"name": "Renamed Employee"}).status_code == 200

    staff = client.post("/api/users", headers=admin_headers, json=_new_user("reviewer")).json()
    assert client.delete(f"/api/users/{staff['id']}", headers=hr_headers).status_code == 403
    assert client.delete(f"/api/users/{staff['id']}", headers=admin_headers).status_code == 200
    assert client.post(f"/api/users/{staff['id']}/restore", headers=admin_headers).status_code == 200


def test_admin_can_create_any_role(client, admin_headers):
    for role in ("admin", "hr", "reviewer", "employee"):
        assert client.post("/api/users", headers=admin_headers, json=_new_user(role)).status_code == 201
