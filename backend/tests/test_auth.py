from datetime import UTC, datetime, timedelta
from typing import Annotated

import jwt
import pytest
from fastapi import Depends
from sqlalchemy import select

from app.api.deps import require_roles
from app.core.config import get_settings
from app.models import User, UserRole


@pytest.mark.parametrize(
    ("email", "role", "title", "department"),
    [
        ("hr@fourangrybirds.vn", "hr", "HR Executive", "Human Resources"),
        ("reviewer@fourangrybirds.vn", "reviewer", "Onboarding Reviewer", "Human Resources"),
        ("alex.morgan@fourangrybirds.vn", "employee", "Software Support Engineer", "Engineering"),
    ],
)
def test_demo_accounts_log_in(client, email, role, title, department):
    res = client.post("/api/auth/login", json={"email": email, "password": "Demo@123"})

    assert res.status_code == 200
    body = res.json()
    assert body["token_type"] == "bearer"
    assert body["expires_in"] > 0
    assert body["user"]["user_role"] == role
    assert body["user"]["title"] == title
    assert body["user"]["department_code"] == department
    assert "password_hash" not in body["user"]


def test_email_is_case_insensitive(client):
    res = client.post("/api/auth/login", json={"email": "HR@FourAngryBirds.vn", "password": "Demo@123"})
    assert res.status_code == 200


@pytest.mark.parametrize(
    ("email", "password"),
    [("hr@fourangrybirds.vn", "wrong-password"), ("nobody@fourangrybirds.vn", "Demo@123")],
)
def test_bad_credentials_get_the_same_401(client, email, password):
    res = client.post("/api/auth/login", json={"email": email, "password": password})

    assert res.status_code == 401
    assert res.json()["detail"] == "Incorrect email or password"


def test_me_returns_current_user(client, employee_headers):
    res = client.get("/api/auth/me", headers=employee_headers)

    assert res.status_code == 200
    assert res.json()["email"] == "alex.morgan@fourangrybirds.vn"
    assert res.json()["job_position_id"] == "support-engineer"


def test_me_requires_token(client):
    res = client.get("/api/auth/me")

    assert res.status_code == 401
    assert res.headers["www-authenticate"] == "Bearer"


def test_tampered_token_is_rejected(client, hr_headers):
    headers = {"Authorization": hr_headers["Authorization"][:-2] + "xx"}
    assert client.get("/api/auth/me", headers=headers).status_code == 401


def test_expired_token_is_rejected(client, db):
    user = db.scalar(select(User).where(User.email == "hr@fourangrybirds.vn"))
    settings = get_settings()
    past = datetime.now(UTC) - timedelta(hours=1)
    token = jwt.encode({"sub": user.id, "role": "hr", "iat": past, "exp": past}, settings.jwt_secret, settings.jwt_algorithm)

    res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert res.status_code == 401
    assert res.json()["detail"] == "Session expired"


def test_disabled_account_loses_access_immediately(client, db, reviewer_headers):
    user = db.scalar(select(User).where(User.email == "reviewer@fourangrybirds.vn"))
    user.is_active = False
    db.commit()
    try:
        assert client.get("/api/auth/me", headers=reviewer_headers).status_code == 401
        login = client.post("/api/auth/login", json={"email": user.email, "password": "Demo@123"})
        assert login.status_code == 401
    finally:
        user.is_active = True
        db.commit()


def test_require_roles_blocks_other_roles(app, client, hr_headers, employee_headers):
    @app.get("/api/_test/hr-only")
    def hr_only(user: Annotated[User, Depends(require_roles(UserRole.HR))]):
        return {"id": user.id}

    assert client.get("/api/_test/hr-only", headers=hr_headers).status_code == 200
    denied = client.get("/api/_test/hr-only", headers=employee_headers)
    assert denied.status_code == 403
    assert client.get("/api/_test/hr-only").status_code == 401
