"""Test setup: a throwaway SQLite database built by the real Alembic migrations, then seeded."""
import os
import smtplib
import tempfile
from pathlib import Path

# Settings are read once at import time, so the test environment must exist before `app` is imported.
_TMP_DIR = Path(tempfile.mkdtemp(prefix="skillsprint-test-"))
TEST_DB_URL = f"sqlite:///{(_TMP_DIR / 'test.db').as_posix()}"
os.environ["DATABASE_URL"] = TEST_DB_URL
os.environ["JWT_SECRET"] = "test-secret-" + "x" * 32
os.environ["UPLOAD_DIR"] = str(_TMP_DIR / "uploads")
# A developer's backend/.env may hold a real key: tests must never call Gemini (cost, quota, flaky results).
# Tests that exercise Pipeline 1 swap in tests/fake_llm.py instead.
os.environ["GEMINI_API_KEY"] = ""
# Same for SMTP: tests that send account emails replace smtplib.SMTP with a fake (see `smtp` fixture).
os.environ["SMTP_HOST"] = ""

import pytest  # noqa: E402
from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.core.config import get_settings  # noqa: E402
from app.db import seed  # noqa: E402
from app.db.session import SessionLocal, engine  # noqa: E402
from app.main import create_app  # noqa: E402

BACKEND_DIR = Path(__file__).resolve().parents[1]


def alembic_config(database_url: str) -> Config:
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    cfg.set_main_option("sqlalchemy.url", database_url)
    return cfg


@pytest.fixture(scope="session", autouse=True)
def database():
    command.upgrade(alembic_config(TEST_DB_URL), "head")
    with SessionLocal() as db:
        seed.run(db)
    yield
    engine.dispose()


@pytest.fixture
def db():
    with SessionLocal() as session:
        yield session


@pytest.fixture
def app():
    return create_app()


@pytest.fixture
def client(app):
    with TestClient(app) as test_client:
        yield test_client


def login(client: TestClient, email: str, password: str = seed.DEMO_PASSWORD) -> dict:
    res = client.post("/api/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200, res.text
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


@pytest.fixture
def hr_headers(client):
    return login(client, "hr@fourangrybirds.vn")


@pytest.fixture
def reviewer_headers(client):
    return login(client, "reviewer@fourangrybirds.vn")


@pytest.fixture
def employee_headers(client):
    return login(client, "alex.morgan@fourangrybirds.vn")


class FakeSMTP:
    sent: list = []
    fail = False

    def __init__(self, host, port, timeout):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def starttls(self):
        if FakeSMTP.fail:
            raise smtplib.SMTPException("relay refused")

    def login(self, user, password):
        pass

    def send_message(self, msg):
        FakeSMTP.sent.append(msg)


@pytest.fixture
def smtp(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "smtp_host", "smtp.test")
    monkeypatch.setattr(settings, "smtp_user", "noreply@fourangrybirds.vn")
    monkeypatch.setattr(settings, "smtp_password", "secret")
    monkeypatch.setattr(smtplib, "SMTP", FakeSMTP)
    FakeSMTP.sent = []
    FakeSMTP.fail = False
    return FakeSMTP
