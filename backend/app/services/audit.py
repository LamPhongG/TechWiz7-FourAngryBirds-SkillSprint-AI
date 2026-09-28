"""Audit trail writes and reads. Writes join the caller's transaction, so an action and its log
row are committed together or not at all."""
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.base import new_id
from app.models import AuditLog, FinalStatus, LearningPath, PathStatus, User


def record(
    db: Session,
    actor: User,
    action: str,
    path: LearningPath,
    *,
    status_before: PathStatus | None,
    status_after: PathStatus | None,
    final_status: FinalStatus | None = None,
    reason: str | None = None,
    details: dict | None = None,
) -> None:
    db.add(AuditLog(
        id=new_id("LOG"),
        actor_id=actor.id,
        actor_name=actor.name,
        actor_role=actor.user_role,
        action=action,
        path_id=path.id,
        path_title=path.title_en,
        revision=path.revision,
        status_before=status_before,
        status_after=status_after,
        final_status=final_status,
        reason=reason,
        details=details,
    ))


def list_logs(
    db: Session, *, path_id: str | None, action: str | None, limit: int, offset: int
) -> tuple[list[AuditLog], int]:
    filters = []
    if path_id:
        filters.append(AuditLog.path_id == path_id)
    if action:
        filters.append(AuditLog.action == action)
    total = db.scalar(select(func.count()).select_from(AuditLog).where(*filters))
    rows = db.scalars(
        select(AuditLog).where(*filters).order_by(AuditLog.created_at.desc(), AuditLog.id.desc()).limit(limit).offset(offset)
    )
    return list(rows), total
