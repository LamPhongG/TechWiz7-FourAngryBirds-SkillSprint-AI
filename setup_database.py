"""SkillSprint AI - Database Setup and Ingestion Script.

Designed for team members and competition evaluators to initialize or reset
the entire application database in a single command.

Usage:
    python setup_database.py            # Initialize missing tables, seed data & ingest 28 docs
    python setup_database.py --reset    # Wipe clean and recreate everything from scratch

What this script sets up:
1. All database tables and relational constraints (13+ tables)
2. 10 Organizational Departments and 10 Job Positions (SRS Step 2)
3. 203 Role Requirement Matrix rules (SRS Step 10 & Table 1)
4. Default Demo Accounts for Admin, HR, Reviewer, and Employees
5. All 28 Company Knowledge Documents (PDF, DOCX, TXT, MD, CSV) with full chunking
6. Demo learning path and employee certificate ready for immediate review
"""
import argparse
import hashlib
import mimetypes
import os
import shutil
import sys
from datetime import date
from pathlib import Path

# Add backend directory to sys.path
SCRIPT_DIR = Path(__file__).resolve().parent
if (SCRIPT_DIR / "app").is_dir():
    BACKEND_DIR = SCRIPT_DIR
    ROOT_DIR = SCRIPT_DIR.parent
elif (SCRIPT_DIR / "backend" / "app").is_dir():
    BACKEND_DIR = SCRIPT_DIR / "backend"
    ROOT_DIR = SCRIPT_DIR
else:
    BACKEND_DIR = Path.cwd() / "backend"
    ROOT_DIR = Path.cwd()

sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import delete, select, text
from app.core.config import get_settings
from app.core.security import hash_password
from app.db.base import Base, new_id, utcnow
from app.db.session import engine, SessionLocal
from app.models import (
    Department,
    Document,
    DocumentChunk,
    Enrollment,
    EnrollmentStatus,
    InjectionFlag,
    JobPosition,
    LearningPath,
    PathLevel,
    PathPurpose,
    PathStatus,
    ProcessingStatus,
    RoleRequirement,
    TrainingStatus,
    User,
    UserRole,
)
from app.db.seed import (
    DEPARTMENTS,
    JOB_POSITIONS,
    DEMO_USERS,
    seed_reference_data,
    seed_demo_users,
    seed_demo_certificate,
    seed_role_matrix,
)
from app.services.document_catalog import CATALOG
from app.ingestion.pipeline import process_file
from app.ingestion.validation import file_extension


SAMPLE_DOCS_MAPPING = {
    "DOC-01": {"file": "DOC-01_employee-handbook_v2.0.md", "version": "2.0", "effective": date(2026, 1, 1), "expiry": None},
    "DOC-02": {"file": "DOC-02_employee-handbook_v1.0.md", "version": "1.0", "effective": date(2024, 1, 1), "expiry": date(2025, 12, 31)},
    "DOC-03": {"file": "DOC-03_hr-leave-policy.docx", "version": "1.0", "effective": date(2026, 1, 1), "expiry": None},
    "DOC-04": {"file": "DOC-04_workplace-conduct-policy.txt", "version": "1.0", "effective": date(2026, 1, 1), "expiry": None},
    "DOC-05": {"file": "DOC-05_data-privacy-policy_v1.0.md", "version": "1.0", "effective": date(2026, 1, 1), "expiry": None},
    "DOC-06": {"file": "DOC-06_information-security-policy_v1.0.md", "version": "1.0", "effective": date(2026, 1, 1), "expiry": None},
    "DOC-07": {"file": "DOC-07_sop-customer-escalation_v1.0.md", "version": "1.0", "effective": date(2026, 1, 1), "expiry": None},
    "DOC-08": {"file": "DOC-08_sop-sales-pipeline_v1.0.md", "version": "1.0", "effective": date(2026, 1, 1), "expiry": None},
    "DOC-09": {"file": "DOC-09_sop-financial-reimbursement_v1.0.md", "version": "1.0", "effective": date(2026, 1, 1), "expiry": None},
    "DOC-10": {"file": "DOC-10_sop-software-deployment-chunks.csv", "version": "1.0", "effective": date(2026, 1, 1), "expiry": None},
    "DOC-11": {"file": "DOC-11_sop-employee-onboarding_v1.0.pdf", "version": "1.0", "effective": date(2026, 1, 1), "expiry": None},
    "DOC-12": {"file": "DOC-12_branch-operations-manual_v1.0.pdf", "version": "1.0", "effective": date(2026, 1, 1), "expiry": None},
    "DOC-13": {"file": "DOC-13_jd-sales-marketing_v1.0.pdf", "version": "1.0", "effective": date(2026, 1, 1), "expiry": None},
    "DOC-14": {"file": "DOC-14_jd-engineering-support_v1.0.pdf", "version": "1.0", "effective": date(2026, 1, 1), "expiry": None},
    "DOC-15": {"file": "DOC-15_jd-hr-finance_v1.0.pdf", "version": "1.0", "effective": date(2026, 1, 1), "expiry": None},
    "DOC-16": {"file": "DOC-16_general-faqs_v1.0.pdf", "version": "1.0", "effective": date(2026, 1, 1), "expiry": None},
    "DOC-17": {"file": "DOC-17_conflicting-policy-sample_v1.0.pdf", "version": "1.0", "effective": date(2026, 1, 1), "expiry": None},
    "DOC-18": {"file": "DOC-18_adversarial-prompt-injection_v1.0.pdf", "version": "1.0", "effective": date(2026, 1, 1), "expiry": None},
    "DOC-19": {"file": "DOC-19_outdated-compliance-rules_v1.0.pdf", "version": "1.0", "effective": date(2026, 1, 1), "expiry": None},
    "DOC-20": {"file": "DOC-20_department-exceptions_v1.0.pdf", "version": "1.0", "effective": date(2026, 1, 1), "expiry": None},
    "DOC-21": {"file": "DOC-21_brand-content-guidelines_v1.0.docx", "version": "1.0", "effective": date(2026, 1, 1), "expiry": None},
    "DOC-22": {"file": "DOC-22_sop-digital-campaign-operations_v1.0.pdf", "version": "1.0", "effective": date(2026, 1, 1), "expiry": None},
    "DOC-23": {"file": "DOC-23_sop-partner-school-session-delivery_v1.0.pdf", "version": "1.0", "effective": date(2026, 1, 1), "expiry": None},
    "DOC-24": {"file": "DOC-24_vendor-procurement-procedure_v1.0.docx", "version": "1.0", "effective": date(2026, 1, 1), "expiry": None},
    "DOC-25": {"file": "DOC-25_data-governance-reporting-standards_v1.0.md", "version": "1.0", "effective": date(2026, 1, 1), "expiry": None},
    "DOC-26": {"file": "DOC-26_metric-definitions_v1.0.csv", "version": "1.0", "effective": date(2026, 1, 1), "expiry": None},
    "DOC-27": {"file": "DOC-27_support-service-standards_v1.0.txt", "version": "1.0", "effective": date(2026, 1, 1), "expiry": None},
    "DOC-28": {"file": "DOC-28_sop-budget-and-month-end-close_v1.0.pdf", "version": "1.0", "effective": date(2026, 1, 1), "expiry": None},
}


def create_schema(reset: bool = False):
    """Create all relational tables."""
    settings = get_settings()
    if reset:
        if settings.database_url.startswith("sqlite:///"):
            db_path = Path(settings.database_url.replace("sqlite:///", ""))
            if db_path.exists():
                print(f"[Reset] Removing existing database file: {db_path.name}")
                db_path.unlink()
        elif "postgresql" in settings.database_url:
            print("[Reset] Dropping and recreating PostgreSQL public schema...")
            with engine.connect() as conn:
                conn.execute(text("DROP SCHEMA public CASCADE; CREATE SCHEMA public;"))
                conn.commit()

    print("[Schema] Initializing database tables...")
    Base.metadata.create_all(bind=engine)
    print(" -> All tables created successfully.")


def ensure_admin_user(db) -> User:
    """Ensure at least one admin account exists for document ownership."""
    admin = db.scalar(select(User).where(User.email == "admin@fourangrybirds.vn"))
    if not admin:
        admin = User(
            id=new_id("USR"),
            email="admin@fourangrybirds.vn",
            name="System Administrator",
            password_hash=hash_password("Demo@123"),
            user_role=UserRole.ADMIN,
            department_code="Company-wide",
            is_active=True,
        )
        db.add(admin)
        db.flush()
    return admin


def ingest_sample_documents(db, admin_id: str):
    """Ingest and chunk all 28 documents from sample_documents/."""
    sample_dir = ROOT_DIR / "sample_documents"
    uploads_dir = get_settings().upload_dir
    uploads_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n[Documents] Ingesting 28 knowledge documents from {sample_dir.name}...")
    ingested_count = 0
    updated_count = 0

    for code, info in SAMPLE_DOCS_MAPPING.items():
        cat = CATALOG.get(code)
        if not cat:
            continue

        file_path = sample_dir / info["file"]
        if not file_path.is_file():
            matches = list(sample_dir.rglob(info["file"]))
            if matches:
                file_path = matches[0]
            else:
                print(f"  [Skip] Missing physical file for {code}: {info['file']}")
                continue

        content = file_path.read_bytes()
        ext = file_extension(file_path.name)
        sha256 = hashlib.sha256(content).hexdigest()

        # Check if already in DB
        existing = db.scalar(select(Document).where(Document.code == code))
        if existing:
            # Check if it has chunks
            chunk_count = db.scalar(select(text("COUNT(*)")).select_from(DocumentChunk).where(DocumentChunk.document_id == existing.id))
            if chunk_count > 0:
                updated_count += 1
                continue

        # Copy file to uploads folder
        storage_filename = f"{code}_{info['version']}_{file_path.name}"
        dest_path = uploads_dir / storage_filename
        dest_path.write_bytes(content)

        # Process chunks
        try:
            res = process_file(content, ext, code)
        except Exception as exc:
            print(f"  [Warning] Extraction issue for {code}: {exc}")
            continue

        doc_id = existing.id if existing else new_id("DV")
        if not existing:
            doc = Document(
                id=doc_id,
                code=code,
                family=cat.family,
                version=info["version"],
                title=cat.title,
                title_en=cat.title_en,
                category=cat.category,
                department_code=cat.department,
                effective_date=info["effective"],
                expiry_date=info["expiry"],
                file_name=file_path.name,
                ext=ext,
                mime_type=mimetypes.guess_type(file_path.name)[0],
                size_bytes=len(content),
                sha256=sha256,
                storage_path=storage_filename,
                processing_status=ProcessingStatus.READY,
                processing_engine="backend",
                page_count=res.page_count,
                char_count=res.char_count,
                processed_at=utcnow(),
                uploaded_by_id=admin_id,
            )
            db.add(doc)
            db.flush()
        else:
            doc = existing
            doc.sha256 = sha256
            doc.storage_path = storage_filename
            doc.processing_status = ProcessingStatus.READY
            doc.page_count = res.page_count
            doc.char_count = res.char_count
            db.flush()

        # Insert chunks
        db.execute(delete(DocumentChunk).where(DocumentChunk.document_id == doc.id))
        db.execute(delete(InjectionFlag).where(InjectionFlag.document_id == doc.id))

        for pos, c in enumerate(res.chunks):
            db.add(
                DocumentChunk(
                    document_id=doc.id,
                    chunk_id=c["chunk_id"],
                    section_id=c.get("section_id"),
                    heading=c.get("heading"),
                    page=c.get("page"),
                    position=pos,
                    content=c["content"],
                )
            )

        for flag in res.injection_flags:
            db.add(
                InjectionFlag(
                    document_id=doc.id,
                    chunk_id=flag["chunk_id"],
                    page=flag.get("page"),
                    rule_id=flag["rule_id"],
                    severity=flag["severity"],
                    match=flag["match"],
                    excerpt=flag["excerpt"],
                )
            )

        ingested_count += 1
        print(f"  + {code}: {cat.title_en} ({len(res.chunks)} chunks)")

    db.commit()
    print(f" -> Document ingestion complete: {ingested_count} newly processed, {updated_count} existing ready.")


def main():
    parser = argparse.ArgumentParser(description="SkillSprint AI - Database Setup & Seeding")
    parser.add_argument("--reset", "-r", action="store_true", help="Reset and recreate database from scratch")
    args = parser.parse_args()

    print("=" * 70)
    print("      SKILLSPRINT AI - DATABASE INITIALIZATION & SEEDING")
    print("=" * 70)

    create_schema(reset=args.reset)

    with SessionLocal() as db:
        print("\n[Seed] Inserting reference data and users...")
        seed_reference_data(db)
        admin = ensure_admin_user(db)
        seed_demo_users(db)
        print(f" -> Seeded {len(DEPARTMENTS)} departments, {len(JOB_POSITIONS)} job positions, {len(DEMO_USERS) + 1} users.")

        print("\n[Matrix] Importing Role Requirement Matrix (203 requirements)...")
        report = seed_role_matrix(db)
        if report:
            print(f" -> Role Matrix: {report.created} created, {report.updated} updated, {len(report.errors)} errors.")

        ingest_sample_documents(db, admin.id)

        print("\n[Demo] Seeding demo path and employee certificate...")
        seed_demo_certificate(db)
        db.commit()

        # Final Verification Counts
        user_cnt = db.scalar(select(text("COUNT(*)")).select_from(User))
        doc_cnt = db.scalar(select(text("COUNT(*)")).select_from(Document))
        chunk_cnt = db.scalar(select(text("COUNT(*)")).select_from(DocumentChunk))
        req_cnt = db.scalar(select(text("COUNT(*)")).select_from(RoleRequirement))

    print("\n" + "=" * 70)
    print("                 SETUP COMPLETED SUCCESSFULLY")
    print("=" * 70)
    print(f"  Database Path : {get_settings().database_url}")
    print(f"  Users         : {user_cnt} active accounts")
    print(f"  Documents     : {doc_cnt}/28 active documents in repository")
    print(f"  Chunks        : {chunk_cnt} verified searchable text chunks")
    print(f"  Role Matrix   : {req_cnt} job requirements loaded")
    print("-" * 70)
    print("  Demo Logins (Password: Demo@123 or password123):")
    print("   - Admin      : admin@fourangrybirds.vn")
    print("   - HR Manager : hr@fourangrybirds.vn")
    print("   - Reviewer   : reviewer@fourangrybirds.vn")
    print("   - Employee   : alex.morgan@fourangrybirds.vn (or sales.emp@fourangrybirds.vn)")
    print("-" * 70)
    print("  To start the application:")
    print("   1. Backend  : cd backend && uvicorn app.main:app --reload --port 8000")
    print("   2. Frontend : cd frontend && npm run dev")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
