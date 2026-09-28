"""Script to reset PostgreSQL skillsprint_db to current schema via Alembic
and synchronize all data from skillsprint.db (SQLite) to PostgreSQL.
"""
import sys
from pathlib import Path

# Ensure backend root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

import psycopg
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, make_url, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db import seed
from app.models import (
    AuditLog,
    Department,
    Document,
    DocumentChunk,
    Enrollment,
    InjectionFlag,
    JobPosition,
    LearningPath,
    PathAssignment,
    PathComment,
    PathSource,
    QuizAttempt,
    User,
)


def reset_pg_schema():
    settings = get_settings()
    url = make_url(settings.database_url)
    print(f"Connecting to PostgreSQL: {url.render_as_string(hide_password=True)}")
    # DROP SCHEMA must never run against the SQLite file or an unintended server; the target comes from .env only.
    if not url.drivername.startswith("postgresql"):
        raise SystemExit(f"DATABASE_URL is not PostgreSQL ({url.drivername}); nothing was changed.")
    conn = psycopg.connect(url.set(drivername="postgresql").render_as_string(hide_password=False), autocommit=True)
    with conn.cursor() as cur:
        print("Dropping and recreating public schema in PostgreSQL...")
        cur.execute("DROP SCHEMA public CASCADE;")
        cur.execute("CREATE SCHEMA public;")
        cur.execute("GRANT ALL ON SCHEMA public TO postgres;")
        cur.execute("GRANT ALL ON SCHEMA public TO public;")
    conn.close()
    print("Clean schema public created.")

def run_alembic_migrations():
    print("Running Alembic migrations (upgrade head)...")
    alembic_cfg = Config("alembic.ini")
    command.upgrade(alembic_cfg, "head")
    print("Alembic migrations completed successfully!")

def sync_data_from_sqlite():
    settings = get_settings()
    sqlite_path = Path(__file__).resolve().parent / "skillsprint.db"
    if not sqlite_path.exists():
        print(f"SQLite database {sqlite_path} does not exist.")
        return

    print(f"Syncing data from {sqlite_path} to PostgreSQL...")
    engine_sqlite = create_engine(f"sqlite:///{sqlite_path.as_posix()}")
    engine_pg = create_engine(settings.database_url)

    models = [
        Department,
        JobPosition,
        User,
        Document,
        DocumentChunk,
        InjectionFlag,
        LearningPath,
        PathAssignment,
        PathSource,
        PathComment,
        Enrollment,
        QuizAttempt,
        AuditLog,
    ]

    with Session(engine_sqlite) as session_sqlite, Session(engine_pg) as session_pg:
        for model in models:
            rows = session_sqlite.scalars(select(model)).all()
            table_name = model.__tablename__
            print(f"Syncing {len(rows)} rows for {table_name}...")
            for row in rows:
                session_sqlite.expunge(row)
                session_pg.merge(row)
            session_pg.commit()
            print(f"-> {table_name}: OK")

    # Run seed to ensure all 10 departments, 10 job positions, and 12 demo users are accurate
    with Session(engine_pg) as session_pg:
        print("Verifying and seeding demo reference data...")
        seed.run(session_pg)
    print("Data synchronization complete!")

if __name__ == "__main__":
    reset_pg_schema()
    run_alembic_migrations()
    sync_data_from_sqlite()
