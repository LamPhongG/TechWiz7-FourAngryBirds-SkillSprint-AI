"""Assigned learning paths and study progress."""
from datetime import date, datetime

from pydantic import BaseModel

from app.models import AssignmentSource, EnrollmentStatus, LearningPath, PathLevel, PathPurpose, User
from app.services.enrollments import EnrollmentView, outline


class QuizAttemptOut(BaseModel):
    at: datetime
    answers: dict[str, int]
    score: int
    total: int


class ProgressOut(BaseModel):
    done: int
    total: int
    percent: int


class EnrollmentOut(BaseModel):
    path_id: str
    status: EnrollmentStatus
    source: AssignmentSource
    assigned_at: datetime
    due_date: date | None
    overdue: bool
    started_at: datetime | None
    completed_at: datetime | None
    lessons_read: list[str]
    tasks_done: list[str]
    # {module_id: attempts, oldest first}, the shape the frontend keeps in `enrollment.quiz`.
    quiz: dict[str, list[QuizAttemptOut]]
    progress: ProgressOut

    @classmethod
    def from_view(cls, v: EnrollmentView) -> "EnrollmentOut":
        e = v.enrollment
        quiz: dict[str, list[QuizAttemptOut]] = {}
        for a in e.quiz_attempts:
            quiz.setdefault(a.module_id, []).append(
                QuizAttemptOut(at=a.submitted_at, answers=a.answers, score=a.score, total=a.total))
        return cls(path_id=e.path_id, status=e.status, source=e.source, assigned_at=e.assigned_at, due_date=e.due_date,
                   overdue=v.overdue, started_at=e.started_at, completed_at=e.completed_at,
                   lessons_read=e.lessons_read, tasks_done=e.tasks_done, quiz=quiz,
                   progress=ProgressOut(done=v.progress.done, total=v.progress.total, percent=v.progress.percent))


class LearnerOut(BaseModel):
    """One employee's row in the path's learner list (HR / Reviewer)."""

    user_id: str
    name: str
    email: str
    department_code: str | None
    job_position_id: str | None
    status: EnrollmentStatus
    source: AssignmentSource
    due_date: date | None
    overdue: bool
    percent: int
    started_at: datetime | None
    completed_at: datetime | None

    @classmethod
    def from_view(cls, user: User, v: EnrollmentView) -> "LearnerOut":
        e = v.enrollment
        return cls(user_id=user.id, name=user.name, email=user.email, department_code=user.department_code,
                   job_position_id=user.job_position_id, status=e.status, source=e.source, due_date=e.due_date,
                   overdue=v.overdue, percent=v.progress.percent, started_at=e.started_at, completed_at=e.completed_at)


class GlobalLearnerOut(BaseModel):
    """Company-wide learner enrollment record for HR and Reviewers."""

    enrollment_id: str
    user_id: str
    name: str
    email: str
    department_code: str | None
    job_position_id: str | None
    job_title: str | None
    path_id: str
    path_title: str
    path_purpose: PathPurpose
    status: EnrollmentStatus
    source: AssignmentSource
    due_date: date | None
    overdue: bool
    percent: int
    started_at: datetime | None
    completed_at: datetime | None
    best_quiz_percent: int | None
    certificate: bool

    @classmethod
    def from_row(cls, user: User, path: LearningPath, v: EnrollmentView) -> "GlobalLearnerOut":
        e = v.enrollment
        title = user.job_title
        if not title and user.job_position:
            title = user.job_position.name
            
        best_quiz_percent = None
        if e.quiz_attempts:
            module_scores = {}
            for a in e.quiz_attempts:
                if a.total > 0:
                    pct = int(a.score / a.total * 100)
                    if a.module_id not in module_scores or pct > module_scores[a.module_id]:
                        module_scores[a.module_id] = pct
            if module_scores:
                best_quiz_percent = int(sum(module_scores.values()) / len(module_scores))

        return cls(
            enrollment_id=str(e.id),
            user_id=user.id,
            name=user.name,
            email=user.email,
            department_code=user.department_code,
            job_position_id=user.job_position_id,
            job_title=title,
            path_id=path.id,
            path_title=path.title,
            path_purpose=path.purpose,
            status=e.status,
            source=e.source,
            due_date=e.due_date,
            overdue=v.overdue,
            percent=v.progress.percent,
            started_at=e.started_at,
            completed_at=e.completed_at,
            best_quiz_percent=best_quiz_percent,
            certificate=(e.status == EnrollmentStatus.COMPLETED)
        )


class TaskDone(BaseModel):
    done: bool


class QuizSubmit(BaseModel):
    answers: dict[str, int]


class QuizResult(BaseModel):
    score: int
    total: int
    passed: bool
    enrollment: EnrollmentOut


class OutlineModule(BaseModel):
    id: str
    title: str
    title_en: str | None
    doc_code: str | None
    lessons: list[str]
    minutes: int
    tasks: int
    questions: int


class OutlineStage(BaseModel):
    key: str
    modules: list[OutlineModule]


class MyEnrollmentSummary(BaseModel):
    status: EnrollmentStatus
    source: AssignmentSource
    due_date: date | None
    percent: int


class ExplorePathOut(BaseModel):
    """A published path of the employee's department, whether or not it is assigned to them."""

    id: str
    title: str
    title_en: str
    purpose: PathPurpose
    level: PathLevel
    duration_days: int | None
    published_at: datetime | None
    departments: list[str]
    job_positions: list[str]
    # Published to this employee's own position (not only to the department).
    for_my_position: bool
    stages: int
    modules: int
    lessons: int
    minutes: int
    enrollment: MyEnrollmentSummary | None
    outline: list[OutlineStage] | None = None

    @classmethod
    def build(cls, path: LearningPath, user: User, view: EnrollmentView | None, with_outline: bool = False) -> "ExplorePathOut":
        tree = outline(path)
        modules = [m for stage in tree for m in stage["modules"]]
        positions = [a.job_position_id for a in path.assignments if a.job_position_id]
        enrollment = None
        if view is not None and view.enrollment.status is not EnrollmentStatus.WITHDRAWN:
            e = view.enrollment
            enrollment = MyEnrollmentSummary(status=e.status, source=e.source, due_date=e.due_date,
                                             percent=view.progress.percent)
        return cls(id=path.id, title=path.title, title_en=path.title_en, purpose=path.purpose, level=path.level,
                   duration_days=path.duration_days, published_at=path.published_at,
                   departments=[a.department_code for a in path.assignments if a.department_code],
                   job_positions=positions, for_my_position=user.job_position_id in positions,
                   stages=len(tree), modules=len(modules), lessons=sum(len(m["lessons"]) for m in modules),
                   minutes=sum(m["minutes"] for m in modules), enrollment=enrollment,
                   outline=tree if with_outline else None)
