"""Giving published learning paths to employees and recording their progress.

Design and decisions: reports/Project_Report.md (§5.3 assignment rules, §5.5 statuses).
"""
from dataclasses import dataclass
from datetime import date, timedelta

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.db.base import utcnow
from app.models import (
    AssignmentSource,
    Enrollment,
    EnrollmentStatus,
    JobPosition,
    LearningPath,
    PathAssignment,
    PathPurpose,
    PathStatus,
    QuizAttempt,
    TrainingStatus,
    User,
    UserRole,
)
from app.services import audit
from app.services.progress import PathProgress, path_progress, score_quiz
from app.services.visibility import COMPANY_WIDE

ACTIVE = (EnrollmentStatus.ASSIGNED, EnrollmentStatus.IN_PROGRESS)


# Assignment


def due_date_for(user: User, path: LearningPath, today: date) -> date | None:
    """Onboarding: joining date + path length; from today when the employee joined too long ago. Promotion: none."""
    if not path.duration_days:
        return None
    due = (user.joining_date or today) + timedelta(days=path.duration_days)
    return due if due >= today else today + timedelta(days=path.duration_days)


def _match(user: User, path: LearningPath) -> AssignmentSource | None:
    """Which publish target of the path covers this employee; the job position wins over the department."""
    positions = {a.job_position_id for a in path.assignments if a.job_position_id}
    departments = {a.department_code for a in path.assignments if a.department_code}
    if user.job_position_id and user.job_position_id in positions:
        return AssignmentSource.AUTO_POSITION
    if COMPANY_WIDE in departments or user.department_code in departments:
        return AssignmentSource.AUTO_DEPARTMENT
    return None


def _eligible(user: User, path: LearningPath) -> bool:
    if user.user_role is not UserRole.EMPLOYEE or not user.is_active:
        return False
    # Decision Q1: onboarding is for employees who have not finished it yet.
    return path.purpose is not PathPurpose.ONBOARDING or user.training_status is not TrainingStatus.COMPLETED


def _assign(db: Session, user: User, path: LearningPath, source: AssignmentSource, today: date) -> Enrollment | None:
    """None when the employee already has this path (also a withdrawn one: it is not silently given back,
    unless it was previously withdrawn due to department_transfer and the employee transferred back)."""
    existing = db.scalar(select(Enrollment).where(Enrollment.user_id == user.id, Enrollment.path_id == path.id))
    if existing:
        if existing.status == EnrollmentStatus.WITHDRAWN and existing.withdrawn_reason == "department_transfer":
            existing.status = EnrollmentStatus.IN_PROGRESS if existing.started_at else EnrollmentStatus.ASSIGNED
            existing.withdrawn_at = None
            existing.withdrawn_reason = None
            existing.due_date = due_date_for(user, path, today)
            return existing
        return None
    enrollment = Enrollment(user_id=user.id, path_id=path.id, source=source, due_date=due_date_for(user, path, today))
    db.add(enrollment)
    return enrollment


def assign_published_path(db: Session, path: LearningPath, actor: User) -> int:
    """Give a just-published path to every employee its publish targets cover.

    Promotion paths follow the same targets until manual assignment exists (design §13, step 3).
    """
    today = date.today()
    count = 0
    for user in db.scalars(select(User).where(User.user_role == UserRole.EMPLOYEE, User.is_active.is_(True))):
        source = _match(user, path)
        if source and _eligible(user, path) and _assign(db, user, path, source, today):
            count += 1
    if count:
        audit.record(db, actor, "assign", path, status_before=path.status, status_after=path.status,
                     details={"source": "auto", "employees": str(count)})
    return count


def assign_onboarding_to(db: Session, user: User) -> int:
    """A new employee: every published onboarding path that targets their department or position.

    Decision Q2: matching several paths (one by department, one by position) gives all of them.
    """
    paths = db.scalars(select(LearningPath).where(LearningPath.status == PathStatus.PUBLISHED,
                                                  LearningPath.purpose == PathPurpose.ONBOARDING)).all()
    today = date.today()
    count = 0
    for path in paths:
        source = _match(user, path)
        if source and _eligible(user, path) and _assign(db, user, path, source, today):
            audit.record(db, user, "assign", path, status_before=path.status, status_after=path.status,
                         details={"source": "auto", "employee": user.email})
            count += 1
    return count


def sync_enrollments_on_user_transfer(db: Session, user: User, actor: User) -> dict:
    """When an employee's department or job position changes:
    1. Withdraw active auto-assigned onboarding paths that no longer target the employee's new department/position.
       (Completed paths, manual/self enrollments, and company-wide paths are preserved).
    2. Reset user.training_status to NOT_STARTED if it was COMPLETED, so they can onboard into the new role.
    3. Auto-assign published onboarding paths for their new department or position.
    """
    if user.user_role is not UserRole.EMPLOYEE or not user.is_active:
        return {"withdrawn": 0, "assigned": 0}

    withdrawn_count = 0

    # 1. Withdraw outdated active auto-assigned paths
    active_rows = db.execute(
        select(Enrollment, LearningPath)
        .join(LearningPath, LearningPath.id == Enrollment.path_id)
        .where(Enrollment.user_id == user.id, Enrollment.status.in_(ACTIVE))
    ).all()

    for enrollment, path in active_rows:
        if enrollment.source in (AssignmentSource.AUTO_DEPARTMENT, AssignmentSource.AUTO_POSITION):
            if _match(user, path) is None:
                enrollment.status = EnrollmentStatus.WITHDRAWN
                enrollment.withdrawn_at = utcnow()
                enrollment.withdrawn_reason = "department_transfer"
                audit.record(
                    db, actor, "withdraw", path,
                    status_before=path.status, status_after=path.status,
                    details={"reason": "department_transfer", "employee": user.email}
                )
                withdrawn_count += 1

    # 2. Reset training_status so the employee is eligible for the new role's onboarding
    if user.training_status == TrainingStatus.COMPLETED:
        user.training_status = TrainingStatus.NOT_STARTED

    # 3. Assign onboarding paths for the new department / position
    assigned_count = assign_onboarding_to(db, user)

    return {"withdrawn": withdrawn_count, "assigned": assigned_count}


def withdraw_for_archived_path(db: Session, path: LearningPath) -> None:
    """Archived path: employees still studying it lose it; completed records stay as they are."""
    for enrollment in db.scalars(select(Enrollment).where(Enrollment.path_id == path.id, Enrollment.status.in_(ACTIVE))):
        enrollment.status = EnrollmentStatus.WITHDRAWN
        enrollment.withdrawn_at = utcnow()
        enrollment.withdrawn_reason = "path_archived"


# Progress of the employee


@dataclass
class EnrollmentView:
    enrollment: Enrollment
    progress: PathProgress
    overdue: bool


def _best_ratios(enrollment: Enrollment) -> dict[str, float]:
    best: dict[str, float] = {}
    for attempt in enrollment.quiz_attempts:
        if attempt.total:
            best[attempt.module_id] = max(best.get(attempt.module_id, 0.0), attempt.score / attempt.total)
    return best


def view(enrollment: Enrollment, path: LearningPath, today: date | None = None) -> EnrollmentView:
    progress = path_progress(path.stages, enrollment.lessons_read, enrollment.tasks_done, _best_ratios(enrollment))
    today = today or date.today()
    overdue = (enrollment.due_date is not None and enrollment.due_date < today and enrollment.status in ACTIVE)
    return EnrollmentView(enrollment, progress, overdue)


def my_enrollments(db: Session, user: User) -> list[EnrollmentView]:
    rows = db.execute(
        select(Enrollment, LearningPath).join(LearningPath, LearningPath.id == Enrollment.path_id)
        .where(Enrollment.user_id == user.id, Enrollment.status != EnrollmentStatus.WITHDRAWN,
               LearningPath.status == PathStatus.PUBLISHED)
        .order_by(Enrollment.assigned_at)
    ).all()
    return [view(e, p) for e, p in rows]


def path_enrollments(db: Session, path: LearningPath) -> list[tuple[User, EnrollmentView]]:
    rows = db.execute(select(Enrollment, User).join(User, User.id == Enrollment.user_id)
                      .where(Enrollment.path_id == path.id).order_by(User.name)).all()
    return [(u, view(e, path)) for e, u in rows]


def all_enrollments(db: Session) -> list[tuple[User, LearningPath, EnrollmentView]]:
    """Return all enrollments across all learning paths, sorted by assignment date."""
    rows = db.execute(
        select(Enrollment, User, LearningPath)
        .join(User, User.id == Enrollment.user_id)
        .join(LearningPath, LearningPath.id == Enrollment.path_id)
        .where(User.is_active.is_(True))
        .order_by(Enrollment.assigned_at.desc())
    ).all()
    return [(u, p, view(e, p)) for e, u, p in rows]


def _studying(db: Session, user: User, path_id: str) -> tuple[Enrollment, LearningPath]:
    enrollment = db.scalar(select(Enrollment).where(Enrollment.user_id == user.id, Enrollment.path_id == path_id))
    path = db.get(LearningPath, path_id)
    if enrollment is None or enrollment.status is EnrollmentStatus.WITHDRAWN or path is None \
            or path.status is not PathStatus.PUBLISHED:
        raise AppError(404, "err_enrollment_not_found", "This learning path is not assigned to you")
    return enrollment, path


def _module_items(path: LearningPath, kind: str) -> dict[str, dict]:
    return {item["id"]: m for stage in path.stages for m in stage["modules"] for item in m[kind]}


def _touch(enrollment: Enrollment, path: LearningPath) -> EnrollmentView:
    """First activity starts the path; finishing every module completes it (once, the date is kept)."""
    now = utcnow()
    if enrollment.started_at is None:
        enrollment.started_at = now
    current = view(enrollment, path)
    if current.progress.complete and enrollment.status is not EnrollmentStatus.COMPLETED:
        enrollment.status = EnrollmentStatus.COMPLETED
        enrollment.completed_at = now
    elif enrollment.status is EnrollmentStatus.ASSIGNED:
        enrollment.status = EnrollmentStatus.IN_PROGRESS
    return view(enrollment, path)


def mark_lesson_read(db: Session, user: User, path_id: str, lesson_id: str) -> EnrollmentView:
    enrollment, path = _studying(db, user, path_id)
    if lesson_id not in _module_items(path, "lessons"):
        raise AppError(404, "err_item_not_found", "No such lesson in this path")
    if lesson_id not in enrollment.lessons_read:
        # A new list, so SQLAlchemy sees the JSON column change.
        enrollment.lessons_read = [*enrollment.lessons_read, lesson_id]
    result = _touch(enrollment, path)
    db.commit()
    return result


def set_task_done(db: Session, user: User, path_id: str, task_id: str, done: bool) -> EnrollmentView:
    enrollment, path = _studying(db, user, path_id)
    if task_id not in _module_items(path, "tasks"):
        raise AppError(404, "err_item_not_found", "No such task in this path")
    others = [t for t in enrollment.tasks_done if t != task_id]
    enrollment.tasks_done = [*others, task_id] if done else others
    result = _touch(enrollment, path)
    db.commit()
    return result


def submit_quiz(db: Session, user: User, path_id: str, module_id: str,
                answers: dict[str, int]) -> tuple[QuizAttempt, EnrollmentView]:
    enrollment, path = _studying(db, user, path_id)
    module = next((m for stage in path.stages for m in stage["modules"] if m["id"] == module_id), None)
    if module is None or not module["quiz"]:
        raise AppError(404, "err_item_not_found", "No quiz for this module")
    known = {q["id"] for q in module["quiz"]}
    answers = {qid: choice for qid, choice in answers.items() if qid in known}
    score, total, _passed = score_quiz(module["quiz"], answers)
    attempt = QuizAttempt(module_id=module_id, answers=answers, score=score, total=total)
    enrollment.quiz_attempts.append(attempt)
    result = _touch(enrollment, path)
    db.commit()
    return attempt, result


# Explore: every published path of the employee's department, to preview or join


def _explore_filter(user: User):
    """Published to the employee's department, to the whole company, or to a position of their department."""
    positions_in_department = select(JobPosition.id).where(JobPosition.department_code == user.department_code)
    return LearningPath.id.in_(
        select(PathAssignment.path_id).where(or_(
            PathAssignment.department_code.in_([COMPANY_WIDE, user.department_code]),
            PathAssignment.job_position_id.in_(positions_in_department),
        ))
    )


def explorable(db: Session, user: User) -> list[tuple[LearningPath, Enrollment | None]]:
    paths = db.scalars(select(LearningPath).where(LearningPath.status == PathStatus.PUBLISHED, _explore_filter(user))
                       .order_by(LearningPath.published_at.desc())).all()
    mine = {e.path_id: e for e in db.scalars(select(Enrollment).where(Enrollment.user_id == user.id))}
    return [(p, mine.get(p.id)) for p in paths]


def explorable_path(db: Session, user: User, path_id: str) -> tuple[LearningPath, Enrollment | None]:
    path = db.scalar(select(LearningPath).where(LearningPath.id == path_id, LearningPath.status == PathStatus.PUBLISHED,
                                                _explore_filter(user)))
    if path is None:
        raise AppError(404, "err_path_not_found", "Learning path not found")
    return path, db.scalar(select(Enrollment).where(Enrollment.user_id == user.id, Enrollment.path_id == path_id))


def outline(path: LearningPath) -> list[dict]:
    """What the path teaches, without lesson text or quiz answers: enough to decide whether to join."""
    return [{
        "key": stage["key"],
        "modules": [{
            "id": m["id"], "title": m.get("title", ""), "title_en": m.get("titleEn"), "doc_code": m.get("doc_code"),
            "lessons": [lesson.get("title") or "" for lesson in m["lessons"]],
            "minutes": sum(lesson.get("minutes") or 0 for lesson in m["lessons"]),
            "tasks": len(m["tasks"]), "questions": len(m["quiz"]),
        } for m in stage["modules"]],
    } for stage in path.stages]


def self_enroll(db: Session, user: User, path_id: str) -> EnrollmentView:
    """An optional path the employee joins: no due date. A withdrawn record is reopened with its progress kept."""
    path, enrollment = explorable_path(db, user, path_id)
    if enrollment is not None and enrollment.status is not EnrollmentStatus.WITHDRAWN:
        raise AppError(409, "err_already_enrolled", "You already have this learning path")
    if enrollment is None:
        enrollment = Enrollment(user_id=user.id, path_id=path.id, source=AssignmentSource.SELF)
        db.add(enrollment)
    else:
        enrollment.status = EnrollmentStatus.IN_PROGRESS if enrollment.started_at else EnrollmentStatus.ASSIGNED
        enrollment.withdrawn_at = enrollment.withdrawn_reason = None
    audit.record(db, user, "enroll", path, status_before=path.status, status_after=path.status,
                 details={"source": "self", "employee": user.email})
    db.commit()
    return view(enrollment, path)
