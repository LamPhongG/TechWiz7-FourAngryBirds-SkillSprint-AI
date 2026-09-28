"""Assignment of a published learning path to one employee, and that employee's progress on it."""
from datetime import date, datetime

from sqlalchemy import ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, str_enum, utcnow
from app.models.enums import AssignmentSource, EnrollmentStatus


class Enrollment(Base):
    """One path given to one employee (the spec's `Employee_LearningPaths`).

    The path content is not copied: published paths are read-only, so the lesson and task ids stored here
    stay valid for as long as anyone can study the path (reports/Project_Report.md §4.1).
    """

    __tablename__ = "enrollments"
    __table_args__ = (
        UniqueConstraint("user_id", "path_id"),
        Index("ix_enrollments_user_status", "user_id", "status"),
        Index("ix_enrollments_path_status", "path_id", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    path_id: Mapped[str] = mapped_column(ForeignKey("learning_paths.id", ondelete="CASCADE"))
    status: Mapped[EnrollmentStatus] = mapped_column(str_enum(EnrollmentStatus, "enrollment_status"),
                                                     default=EnrollmentStatus.ASSIGNED)
    source: Mapped[AssignmentSource] = mapped_column(str_enum(AssignmentSource, "assignment_source"))
    # Null when the system assigned the path (onboarding rule).
    assigned_by_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    assigned_at: Mapped[datetime] = mapped_column(default=utcnow)
    due_date: Mapped[date | None]
    note: Mapped[str | None] = mapped_column(Text)
    lessons_read: Mapped[list] = mapped_column(default=list)
    tasks_done: Mapped[list] = mapped_column(default=list)
    # Set by the employee's first lesson, task or quiz, not by the assignment.
    started_at: Mapped[datetime | None]
    completed_at: Mapped[datetime | None]
    withdrawn_at: Mapped[datetime | None]
    withdrawn_reason: Mapped[str | None] = mapped_column(String(255))

    quiz_attempts: Mapped[list["QuizAttempt"]] = relationship(
        cascade="all, delete-orphan", passive_deletes=True, order_by="QuizAttempt.submitted_at"
    )


class QuizAttempt(Base):
    __tablename__ = "quiz_attempts"

    id: Mapped[int] = mapped_column(primary_key=True)
    enrollment_id: Mapped[int] = mapped_column(ForeignKey("enrollments.id", ondelete="CASCADE"), index=True)
    module_id: Mapped[str] = mapped_column(String(64))
    # {question_id: chosen option index}
    answers: Mapped[dict]
    score: Mapped[int]
    total: Mapped[int]
    submitted_at: Mapped[datetime] = mapped_column(default=utcnow)
