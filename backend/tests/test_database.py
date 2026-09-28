"""Schema-level guarantees: migrations match the models, constraints hold, seeding is repeatable."""
import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError, OperationalError, StatementError

from app.db import seed
from app.db.base import Base, new_id
from app.db.session import build_engine, engine
from app.models import AuditLog, Department, JobPosition, LearningPath, PathAssignment, PathStatus, User
from tests.conftest import alembic_config


def test_migrations_match_models():
    """Fails when a model changes without a new Alembic revision."""
    with engine.connect() as conn:
        ctx = MigrationContext.configure(conn, opts={"compare_type": True, "render_as_batch": True})
        diff = compare_metadata(ctx, Base.metadata)
    assert diff == []


def test_seed_is_idempotent(db):
    user_ids = set(db.scalars(select(User.id)))

    seed.run(db)

    assert db.scalar(select(func.count()).select_from(Department)) == len(seed.DEPARTMENTS)
    assert db.scalar(select(func.count()).select_from(JobPosition)) == len(seed.JOB_POSITIONS)
    assert set(db.scalars(select(User.id))) == user_ids


def test_passwords_are_hashed(db):
    for user in db.scalars(select(User)):
        assert user.password_hash.startswith("$2")
        assert seed.DEMO_PASSWORD not in user.password_hash


def _hr_user(db) -> User:
    return db.scalar(select(User).where(User.email == "hr@fourangrybirds.vn"))


def _path(db, **overrides) -> LearningPath:
    values = {
        "id": new_id("LP"),
        "title": "Hội nhập — Kỹ sư Hỗ trợ",
        "title_en": "Onboarding — Software Support Engineer",
        "purpose": "onboarding",
        "level": "Intermediate",
        "target_job_position_id": "support-engineer",
        "target_department_code": "Engineering",
        "prompt_version": "v1.0",
        "engine": "local-draft",
        "created_by_id": _hr_user(db).id,
    } | overrides
    return LearningPath(**values)


def test_learning_path_defaults_and_json_roundtrip(db):
    stages = [{"key": "day1", "modules": [{"id": "M1", "lessons": [{"id": "L1", "title": "Chào mừng"}]}]}]
    path = _path(db, stages=stages)
    db.add(path)
    db.commit()
    db.expire_all()

    stored = db.get(LearningPath, path.id)
    assert stored.status is PathStatus.DRAFT
    assert stored.revision == 1
    assert stored.stages == stages
    assert stored.excluded_chunks == []
    db.delete(stored)
    db.commit()


def test_unknown_enum_value_is_rejected(db):
    db.add(_path(db, status="deleted"))
    with pytest.raises((StatementError, LookupError)):
        db.flush()
    db.rollback()


def test_assignment_needs_a_target(db):
    path = _path(db)
    db.add(path)
    db.flush()
    db.add(PathAssignment(path_id=path.id))
    with pytest.raises(IntegrityError):
        db.flush()
    db.rollback()


def test_foreign_keys_are_enforced_on_sqlite(db):
    db.add(_path(db, target_job_position_id="no-such-position"))
    with pytest.raises(IntegrityError):
        db.flush()
    db.rollback()


def test_audit_log_survives_path_deletion(db):
    user = _hr_user(db)
    path = _path(db)
    db.add(path)
    db.flush()
    log = AuditLog(
        id=new_id("LOG"), actor_id=user.id, actor_name=user.name, actor_role=user.user_role,
        action="delete", path_id=path.id, path_title=path.title_en, status_before=PathStatus.DRAFT,
    )
    db.add(log)
    db.delete(path)
    db.commit()

    assert db.get(AuditLog, log.id).path_id == path.id


def test_upgrade_keeps_rows_that_reference_rebuilt_tables(tmp_path):
    """SQLite batch mode rebuilds `users` (copy, drop, rename). Existing rows pointing at users must survive it."""
    url = f"sqlite:///{(tmp_path / 'existing.db').as_posix()}"
    cfg = alembic_config(url)
    command.upgrade(cfg, "56977cdd23d0")
    old = build_engine(url)
    with old.begin() as conn:
        conn.execute(text("INSERT INTO departments (code, name, name_en) VALUES ('HR', 'Nhân sự', 'HR')"))
        conn.execute(text("INSERT INTO users (id, email, password_hash, name, user_role, department_code, is_active, "
                          "created_at) VALUES ('U1', 'a@b.vn', 'x', 'A', 'hr', 'HR', 1, '2026-09-01 00:00:00')"))
        conn.execute(text("INSERT INTO audit_logs (id, created_at, actor_id, actor_name, actor_role, action) "
                          "VALUES ('LOG-1', '2026-09-01 00:00:00', 'U1', 'A', 'hr', 'upload')"))
    old.dispose()

    command.upgrade(cfg, "head")

    new = build_engine(url)
    with new.connect() as conn:
        assert conn.execute(text("SELECT actor_id FROM audit_logs")).scalar_one() == "U1"
        assert conn.execute(text("SELECT competencies FROM users WHERE id = 'U1'")).scalar_one() == "[]"
        assert conn.execute(text("PRAGMA foreign_key_check")).fetchall() == []
        assert conn.execute(text("SELECT name FROM sqlite_master WHERE name LIKE '_alembic_tmp%'")).fetchall() == []
    new.dispose()


def test_failed_sqlite_migration_leaves_nothing_behind(tmp_path):
    """A migration that fails midway rolls back completely instead of leaving half-built tables."""
    url = f"sqlite:///{(tmp_path / 'broken.db').as_posix()}"
    cfg = alembic_config(url)
    command.upgrade(cfg, "56977cdd23d0")
    old = build_engine(url)
    with old.begin() as conn:
        # Batch mode needs this name to rebuild `users`, so the next revision fails after its earlier steps have run.
        conn.execute(text("CREATE TABLE _alembic_tmp_users (id INTEGER)"))
    tables_before = _table_names(old)
    old.dispose()

    with pytest.raises(OperationalError):
        command.upgrade(cfg, "head")

    check = build_engine(url)
    assert _table_names(check) == tables_before
    with check.connect() as conn:
        assert conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == "56977cdd23d0"
    check.dispose()


def _table_names(eng) -> set[str]:
    with eng.connect() as conn:
        return {row[0] for row in conn.execute(text("SELECT name FROM sqlite_master WHERE type = 'table'"))}
