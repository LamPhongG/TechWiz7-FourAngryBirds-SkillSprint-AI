"""Append-only audit trail of every learning-path action."""
from datetime import datetime

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, str_enum, utcnow
from app.models.enums import FinalStatus, PathStatus, UserRole


class AuditLog(Base):
    """One row per action. Rows are only inserted, never updated or deleted.

    `path_id` is deliberately not a foreign key: deleting a draft must not erase its history.
    Actor name and role are copied for the same reason.
    """

    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(default=utcnow, index=True)
    actor_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    actor_name: Mapped[str] = mapped_column(String(128))
    actor_role: Mapped[UserRole] = mapped_column(str_enum(UserRole, "actor_role"))
    # generate, regenerate, edit, submit, resubmit, request_changes, approve, archive, delete, comment
    action: Mapped[str] = mapped_column(String(32), index=True)
    path_id: Mapped[str | None] = mapped_column(String(32), index=True)
    path_title: Mapped[str | None] = mapped_column(String(255))
    revision: Mapped[int | None]
    status_before: Mapped[PathStatus | None] = mapped_column(str_enum(PathStatus, "status_before"))
    status_after: Mapped[PathStatus | None] = mapped_column(str_enum(PathStatus, "status_after"))
    final_status: Mapped[FinalStatus | None] = mapped_column(str_enum(FinalStatus, "final_status"))
    reason: Mapped[str | None] = mapped_column(Text)
    details: Mapped[dict | None]
