"""Reference data and demo accounts. Idempotent: re-running updates rows instead of duplicating them.

Run from `backend/`:  python -m app.db.seed
Values mirror frontend/src/data/company.js and the demo logins in frontend/src/hooks/useAuth.js.
"""
from datetime import UTC, date

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.config import BACKEND_DIR
from app.core.security import hash_password
from app.db.base import new_id
from app.db.session import SessionLocal
from app.models import (
    AssignmentSource,
    Department,
    Enrollment,
    EnrollmentStatus,
    JobPosition,
    LearningPath,
    PathAssignment,
    PathLevel,
    PathStatus,
    QuizAttempt,
    TrainingStatus,
    User,
    UserRole,
)
from app.services.role_matrix import ImportReport, import_csv

DEPARTMENTS = [
    ("Company-wide", "Company-wide"),
    ("Sales", "Sales"),
    ("Customer Support", "Customer Support"),
    ("Human Resources", "Human Resources"),
    ("Finance", "Finance"),
    ("Operations", "Operations"),
    ("Marketing", "Marketing"),
    ("Engineering", "Engineering"),
    ("Branch Management", "Branch Management"),
    ("Data", "Data"),
]

JOB_POSITIONS = [
    ("sales-exec", "Sales Executive", "Sales Executive", "Sales"),
    ("cs-exec", "Customer Support Executive", "Customer Support Executive", "Customer Support"),
    ("hr-exec", "HR Executive", "HR Executive", "Human Resources"),
    ("finance-associate", "Finance Associate", "Finance Associate", "Finance"),
    ("ops-coordinator", "Operations Coordinator", "Operations Coordinator", "Operations"),
    ("marketing-exec", "Marketing Executive", "Marketing Executive", "Marketing"),
    ("support-engineer", "Software Support Engineer", "Software Support Engineer", "Engineering"),
    ("branch-manager", "Branch Manager", "Branch Manager", "Branch Management"),
    ("data-analyst", "Data Analyst", "Data Analyst", "Data"),
    ("team-leader", "Team Leader / Tech Lead", "Team Leader / Tech Lead", "Engineering"),
]

# Demo password is public in the frontend source, so these accounts are for local/demo databases only.
DEMO_PASSWORD = "Demo@123"
DEMO_USERS = [
    # SRS Deliverable 14 asks for an administrator login; the frontend's demo login already offers this account.
    {"email": "admin@fourangrybirds.vn", "name": "Alexandre Admin", "user_role": UserRole.ADMIN,
     "job_title": "System Administrator", "department_code": "Company-wide", "job_position_id": None},
    {"email": "hr@fourangrybirds.vn", "name": "Jordan Lee", "user_role": UserRole.HR,
     "job_title": "HR Executive", "department_code": "Human Resources", "job_position_id": None},
    {"email": "reviewer@fourangrybirds.vn", "name": "Sarah Chen", "user_role": UserRole.REVIEWER,
     "job_title": "Onboarding Reviewer", "department_code": "Human Resources", "job_position_id": None},
    # Listed before Alex because she is his reporting manager.
    {"email": "minh.nguyen@fourangrybirds.vn", "name": "Minh Nguyen", "user_role": UserRole.EMPLOYEE,
     "job_title": None, "department_code": "Engineering", "job_position_id": "team-leader",
     "employee_code": "EMP-0007", "experience_level": PathLevel.ADVANCED, "location": "Ho Chi Minh City",
     "joining_date": date(2023, 3, 1), "competencies": ["Deployment sign-off", "Tier 2 escalation ownership"],
     "previous_experience": "6 years as backend engineer", "training_status": TrainingStatus.COMPLETED},
    {"email": "alex.morgan@fourangrybirds.vn", "name": "Alex Morgan", "user_role": UserRole.EMPLOYEE,
     "job_title": None, "department_code": "Engineering", "job_position_id": "support-engineer",
     "employee_code": "EMP-0142", "experience_level": PathLevel.INTERMEDIATE, "location": "Ho Chi Minh City",
     "joining_date": date(2026, 9, 21), "manager_email": "minh.nguyen@fourangrybirds.vn",
     "competencies": ["Pre-deployment checklist", "Customer handover"],
     "previous_experience": "2 years of IT helpdesk", "training_status": TrainingStatus.NOT_STARTED},
    # A new hire in Customer Support, so the SRS worked example (R001, DOC-07 §4.2) can be followed as an employee.
    {"email": "linh.tran@fourangrybirds.vn", "name": "Linh Tran", "user_role": UserRole.EMPLOYEE,
     "job_title": None, "department_code": "Customer Support", "job_position_id": "cs-exec",
     "employee_code": "EMP-0158", "experience_level": PathLevel.BEGINNER, "location": "Ho Chi Minh City",
     "joining_date": date(2026, 9, 28), "competencies": ["Tier 1 response", "Escalation judgment"],
     "previous_experience": "1 year in retail customer service", "training_status": TrainingStatus.NOT_STARTED},

    {"email": "sales.emp@fourangrybirds.vn", "name": "Sales Employee", "user_role": UserRole.EMPLOYEE, "job_title": None, "department_code": "Sales", "job_position_id": "sales-exec", "employee_code": "EMP-0201", "experience_level": PathLevel.BEGINNER, "location": "Hanoi", "joining_date": date(2026, 8, 1), "training_status": TrainingStatus.NOT_STARTED},
    {"email": "cs.emp@fourangrybirds.vn", "name": "CS Employee", "user_role": UserRole.EMPLOYEE, "job_title": None, "department_code": "Customer Support", "job_position_id": "cs-exec", "employee_code": "EMP-0202", "experience_level": PathLevel.BEGINNER, "location": "Hanoi", "joining_date": date(2026, 8, 1), "training_status": TrainingStatus.NOT_STARTED},
    {"email": "hr.emp@fourangrybirds.vn", "name": "HR Employee", "user_role": UserRole.EMPLOYEE, "job_title": None, "department_code": "Human Resources", "job_position_id": "hr-exec", "employee_code": "EMP-0203", "experience_level": PathLevel.BEGINNER, "location": "Hanoi", "joining_date": date(2026, 8, 1), "training_status": TrainingStatus.NOT_STARTED},
    {"email": "finance.emp@fourangrybirds.vn", "name": "Finance Employee", "user_role": UserRole.EMPLOYEE, "job_title": None, "department_code": "Finance", "job_position_id": "finance-associate", "employee_code": "EMP-0204", "experience_level": PathLevel.BEGINNER, "location": "Hanoi", "joining_date": date(2026, 8, 1), "training_status": TrainingStatus.NOT_STARTED},
    {"email": "ops.emp@fourangrybirds.vn", "name": "Ops Employee", "user_role": UserRole.EMPLOYEE, "job_title": None, "department_code": "Operations", "job_position_id": "ops-coordinator", "employee_code": "EMP-0205", "experience_level": PathLevel.BEGINNER, "location": "Hanoi", "joining_date": date(2026, 8, 1), "training_status": TrainingStatus.NOT_STARTED},
    {"email": "marketing.emp@fourangrybirds.vn", "name": "Marketing Employee", "user_role": UserRole.EMPLOYEE, "job_title": None, "department_code": "Marketing", "job_position_id": "marketing-exec", "employee_code": "EMP-0206", "experience_level": PathLevel.BEGINNER, "location": "Hanoi", "joining_date": date(2026, 8, 1), "training_status": TrainingStatus.NOT_STARTED},
    {"email": "branch.mgr@fourangrybirds.vn", "name": "Branch Manager", "user_role": UserRole.EMPLOYEE, "job_title": None, "department_code": "Branch Management", "job_position_id": "branch-manager", "employee_code": "EMP-0207", "experience_level": PathLevel.BEGINNER, "location": "Hanoi", "joining_date": date(2026, 8, 1), "training_status": TrainingStatus.NOT_STARTED},
    {"email": "data.analyst@fourangrybirds.vn", "name": "Data Analyst", "user_role": UserRole.EMPLOYEE, "job_title": None, "department_code": "Data", "job_position_id": "data-analyst", "employee_code": "EMP-0208", "experience_level": PathLevel.BEGINNER, "location": "Hanoi", "joining_date": date(2026, 8, 1), "training_status": TrainingStatus.NOT_STARTED},
    {"email": "team.lead@fourangrybirds.vn", "name": "Tech Lead", "user_role": UserRole.EMPLOYEE, "job_title": None, "department_code": "Engineering", "job_position_id": "team-leader", "employee_code": "EMP-0209", "experience_level": PathLevel.ADVANCED, "location": "Hanoi", "joining_date": date(2026, 8, 1), "training_status": TrainingStatus.COMPLETED},
]

ROLE_MATRIX_CSV = BACKEND_DIR.parent / "role_matrix" / "role_matrix.csv"


def seed_reference_data(db: Session) -> None:
    for code, name in DEPARTMENTS:
        db.merge(Department(code=code, name=name, name_en=code))
    db.flush()
    for pos_id, name, name_en, dept in JOB_POSITIONS:
        db.merge(JobPosition(id=pos_id, name=name, name_en=name_en, department_code=dept))
    db.flush()


def seed_demo_users(db: Session) -> None:
    password_hash = hash_password(DEMO_PASSWORD)
    for entry in DEMO_USERS:
        account = {k: v for k, v in entry.items() if k != "manager_email"}
        if entry.get("manager_email"):
            account["manager_id"] = db.scalar(select(User.id).where(User.email == entry["manager_email"]))
        user = db.scalar(select(User).where(User.email == account["email"]))
        if user is None:
            db.add(User(id=new_id("USR"), password_hash=password_hash, **account))
            db.flush()
            continue
        # Existing rows keep their id (audit logs point at it) but get the canonical profile back.
        for field, value in account.items():
            setattr(user, field, value)
        user.password_hash = password_hash
        user.is_active = True


def seed_demo_certificate(db: Session) -> None:
    """Give the Sales demo employee one completed path, so the certificate screen has something to show.

    Only a path the Reviewer actually published to Sales (department or sales-exec) qualifies. Faking a path, or
    picking any row, once marked a Branch Manager path still in review as completed and led to it being published
    by hand without targets, which crashed the HR dashboard. With no such path yet, nothing is seeded.
    """
    from datetime import datetime
    
    sales_id = db.scalar(select(User.id).where(User.email == "sales.emp@fourangrybirds.vn"))
    if sales_id is None:
        return
    path_id = db.scalar(
        select(LearningPath.id)
        .join(PathAssignment, PathAssignment.path_id == LearningPath.id)
        .where(LearningPath.status == PathStatus.PUBLISHED,
               or_(PathAssignment.department_code == "Sales", PathAssignment.job_position_id == "sales-exec"))
        .order_by(LearningPath.published_at)
        .limit(1)
    )
    if path_id is None:
        return
    enrollment = db.scalar(select(Enrollment).where(Enrollment.user_id == sales_id, Enrollment.path_id == path_id))
    if enrollment is not None and enrollment.status == EnrollmentStatus.COMPLETED:
        return
    now = datetime.now(UTC)
    if enrollment is None:
        enrollment = Enrollment(user_id=sales_id, path_id=path_id, source=AssignmentSource.SELF, assigned_at=now)
        db.add(enrollment)
    modules = [m for stage in db.get(LearningPath, path_id).stages for m in stage["modules"]]
    enrollment.lessons_read = [lesson["id"] for m in modules for lesson in m.get("lessons", [])]
    enrollment.tasks_done = [task["id"] for m in modules for task in m.get("tasks", [])]
    enrollment.status = EnrollmentStatus.COMPLETED
    enrollment.started_at = enrollment.started_at or now
    enrollment.completed_at = now
    db.flush()
    for m in modules:
        quiz = m.get("quiz", [])
        if quiz:
            db.add(QuizAttempt(enrollment_id=enrollment.id, module_id=m["id"], submitted_at=now,
                               answers={q["id"]: q["answer"] for q in quiz}, score=len(quiz), total=len(quiz)))
    db.flush()


def seed_role_matrix(db: Session) -> ImportReport | None:
    """Load the team's Role Requirement Matrix; rows already in the DB are updated, not duplicated."""
    if not ROLE_MATRIX_CSV.is_file():
        return None
    return import_csv(db, ROLE_MATRIX_CSV.read_text(encoding="utf-8"))


def run(db: Session) -> ImportReport | None:
    seed_reference_data(db)
    seed_demo_users(db)
    seed_demo_certificate(db)
    report = seed_role_matrix(db)
    db.commit()
    return report


if __name__ == "__main__":
    with SessionLocal() as session:
        matrix = run(session)
    print(f"Seeded {len(DEPARTMENTS)} departments, {len(JOB_POSITIONS)} job positions, {len(DEMO_USERS)} demo users.")
    if matrix:
        print(f"Role matrix: {matrix.created} created, {matrix.updated} updated, {len(matrix.errors)} errors")
        for error in matrix.errors:
            print("  ", error)
