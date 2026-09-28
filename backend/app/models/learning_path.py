"""Learning paths and everything attached to them: sources, publish targets, review comments."""
from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, str_enum, utcnow
from app.models.enums import FinalStatus, PathLevel, PathPurpose, PathStatus


class LearningPath(Base):
    """A generated learning path moving through draft → in_review → published → archived.

    `stages` holds the whole stage → module → lesson/task/quiz tree as JSON (contract in
    reports/Project_Report.md §7). HR and Reviewers edit and review the tree as one unit, and
    every item keeps its own `source_reference`, so splitting it into tables would only add joins.
    """

    __tablename__ = "learning_paths"
    __table_args__ = (Index("ix_learning_paths_status_updated", "status", "updated_at"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    title: Mapped[str] = mapped_column(String(255))
    title_en: Mapped[str] = mapped_column(String(255))
    purpose: Mapped[PathPurpose] = mapped_column(str_enum(PathPurpose, "purpose"))
    level: Mapped[PathLevel] = mapped_column(str_enum(PathLevel, "level"))
    target_job_position_id: Mapped[str] = mapped_column(ForeignKey("job_positions.id"))
    target_department_code: Mapped[str] = mapped_column(ForeignKey("departments.code"))
    # Set for a personal plan built from one employee's profile (SRS Step 12); null for a role-wide plan.
    employee_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    # Onboarding length chosen by HR (7, 30 or 90 days; SRS Step 13); it limits the stages the path may use.
    # Null for promotion paths, which are phase-based.
    duration_days: Mapped[int | None]

    prompt: Mapped[str | None] = mapped_column(Text)
    prompt_version: Mapped[str] = mapped_column(String(16))
    # "gemini" when Pipeline 1 generated the content, "local-draft" for the rule-based fallback.
    engine: Mapped[str] = mapped_column(String(32))
    model: Mapped[str | None] = mapped_column(String(64))

    stages: Mapped[list] = mapped_column(default=list)
    excluded_chunks: Mapped[list] = mapped_column(default=list)
    # Pipeline 2 result: {score, requiredDocs, topics}; null until the rule engine has run.
    coverage: Mapped[dict | None]
    # Pipeline 1 report: model, tokens, duration, per-module engine and grounding drops (see genai_pipeline).
    generation: Mapped[dict | None]

    status: Mapped[PathStatus] = mapped_column(str_enum(PathStatus, "status"), default=PathStatus.DRAFT)
    revision: Mapped[int] = mapped_column(default=1)

    created_by_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow)
    submitted_at: Mapped[datetime | None]
    published_at: Mapped[datetime | None]
    archived_at: Mapped[datetime | None]

    approved_by_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    approval_final_status: Mapped[FinalStatus | None] = mapped_column(str_enum(FinalStatus, "approval_final_status"))
    approval_reason: Mapped[str | None] = mapped_column(Text)

    sources: Mapped[list["PathSource"]] = relationship(
        cascade="all, delete-orphan", passive_deletes=True, order_by="PathSource.position"
    )
    assignments: Mapped[list["PathAssignment"]] = relationship(cascade="all, delete-orphan", passive_deletes=True)
    comments: Mapped[list["PathComment"]] = relationship(
        cascade="all, delete-orphan", passive_deletes=True, order_by="PathComment.created_at"
    )


class PathSource(Base):
    """Document version a path was generated from.

    Code and version are copied so the path still names its source after the document row is deleted.
    """

    __tablename__ = "path_sources"

    id: Mapped[int] = mapped_column(primary_key=True)
    path_id: Mapped[str] = mapped_column(ForeignKey("learning_paths.id", ondelete="CASCADE"), index=True)
    document_id: Mapped[str | None] = mapped_column(ForeignKey("documents.id", ondelete="SET NULL"))
    doc_code: Mapped[str] = mapped_column(String(32))
    doc_version: Mapped[str] = mapped_column(String(16))
    position: Mapped[int]


class PathAssignment(Base):
    """Publish target of a path: a department or a job position. Who actually studies it is in `enrollments`."""

    __tablename__ = "path_assignments"
    __table_args__ = (CheckConstraint("department_code IS NOT NULL OR job_position_id IS NOT NULL", name="has_target"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    path_id: Mapped[str] = mapped_column(ForeignKey("learning_paths.id", ondelete="CASCADE"), index=True)
    department_code: Mapped[str | None] = mapped_column(ForeignKey("departments.code"), index=True)
    job_position_id: Mapped[str | None] = mapped_column(ForeignKey("job_positions.id"), index=True)


class PathComment(Base):
    """Reviewer ↔ HR discussion, optionally pinned to one lesson / task / question in `stages`."""

    __tablename__ = "path_comments"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    path_id: Mapped[str] = mapped_column(ForeignKey("learning_paths.id", ondelete="CASCADE"), index=True)
    author_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    text: Mapped[str] = mapped_column(Text)
    # {"id": "<item id inside stages>", "label": "..."}
    item_ref: Mapped[dict | None]
    reply_to_id: Mapped[str | None] = mapped_column(ForeignKey("path_comments.id", ondelete="SET NULL"))
    resolved: Mapped[bool] = mapped_column(default=False)
    resolved_by_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
