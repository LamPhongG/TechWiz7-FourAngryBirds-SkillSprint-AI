from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.deps import DbSession, require_roles
from app.models import User, UserRole
from app.schemas.paths import AuditLogPage
from app.services import audit as service

router = APIRouter(tags=["audit"])


@router.get("/audit-logs", response_model=AuditLogPage)
def list_audit_logs(
    db: DbSession,
    _user: Annotated[User, Depends(require_roles(UserRole.HR, UserRole.REVIEWER, UserRole.ADMIN))],
    path_id: str | None = None,
    action: str | None = None,
    limit: Annotated[int, Query(ge=1, le=1000)] = 200,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    """Newest first. Filter by path or action; page with limit / offset."""
    rows, total = service.list_logs(db, path_id=path_id, action=action, limit=limit, offset=offset)
    return AuditLogPage(items=rows, total=total)
