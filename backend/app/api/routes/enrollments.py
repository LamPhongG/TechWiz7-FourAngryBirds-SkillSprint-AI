"""Paths assigned to the signed-in employee, their progress, and the department paths they can explore and join;
learner lists for HR and Reviewers."""
from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import DbSession, require_roles
from app.models import User, UserRole
from app.schemas.enrollments import EnrollmentOut, ExplorePathOut, GlobalLearnerOut, LearnerOut, QuizResult, QuizSubmit, TaskDone
from app.services import enrollments as service
from app.services.paths import get_visible
from app.services.progress import PASS_RATIO

router = APIRouter(tags=["enrollments"])

Employee = Annotated[User, Depends(require_roles(UserRole.EMPLOYEE))]
# Learner progress endpoints accessible to staff and admin users.
Staff = Annotated[User, Depends(require_roles(UserRole.HR, UserRole.REVIEWER, UserRole.ADMIN))]


@router.get("/learners", response_model=list[GlobalLearnerOut])
def all_learners(db: DbSession, user: Staff):
    """Company-wide learner progress across all paths (HR and Reviewer)."""
    return [GlobalLearnerOut.from_row(u, p, v) for u, p, v in service.all_enrollments(db)]


@router.get("/me/enrollments", response_model=list[EnrollmentOut])
def my_enrollments(db: DbSession, user: Employee):
    return [EnrollmentOut.from_view(v) for v in service.my_enrollments(db, user)]


@router.post("/me/enrollments/{path_id}/lessons/{lesson_id}", response_model=EnrollmentOut)
def mark_lesson_read(path_id: str, lesson_id: str, db: DbSession, user: Employee):
    return EnrollmentOut.from_view(service.mark_lesson_read(db, user, path_id, lesson_id))


@router.put("/me/enrollments/{path_id}/tasks/{task_id}", response_model=EnrollmentOut)
def set_task(path_id: str, task_id: str, body: TaskDone, db: DbSession, user: Employee):
    return EnrollmentOut.from_view(service.set_task_done(db, user, path_id, task_id, body.done))


@router.post("/me/enrollments/{path_id}/quizzes/{module_id}", response_model=QuizResult)
def submit_quiz(path_id: str, module_id: str, body: QuizSubmit, db: DbSession, user: Employee):
    attempt, view = service.submit_quiz(db, user, path_id, module_id, body.answers)
    return QuizResult(score=attempt.score, total=attempt.total, passed=attempt.score / attempt.total >= PASS_RATIO,
                      enrollment=EnrollmentOut.from_view(view))


@router.get("/paths/{path_id}/enrollments", response_model=list[LearnerOut])
def path_learners(path_id: str, db: DbSession, user: Staff):
    path = get_visible(db, user, path_id)
    return [LearnerOut.from_view(u, v) for u, v in service.path_enrollments(db, path)]


@router.get("/explore/paths", response_model=list[ExplorePathOut])
def explore_paths(db: DbSession, user: Employee):
    return [ExplorePathOut.build(p, user, service.view(e, p) if e else None) for p, e in service.explorable(db, user)]


@router.get("/explore/paths/{path_id}", response_model=ExplorePathOut)
def explore_path(path_id: str, db: DbSession, user: Employee):
    path, enrollment = service.explorable_path(db, user, path_id)
    return ExplorePathOut.build(path, user, service.view(enrollment, path) if enrollment else None, with_outline=True)


@router.post("/explore/paths/{path_id}/enroll", response_model=EnrollmentOut, status_code=201)
def enroll(path_id: str, db: DbSession, user: Employee):
    return EnrollmentOut.from_view(service.self_enroll(db, user, path_id))
