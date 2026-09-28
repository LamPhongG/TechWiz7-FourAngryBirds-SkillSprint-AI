from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession, require_roles
from app.core.errors import AppError
from app.models import Department, JobPosition, User, UserRole
from app.schemas.catalog import DepartmentOut, JobPositionOut, RequiredSourceOut
from app.services import role_matrix

router = APIRouter(tags=["catalog"])

# Endpoints accessible to staff and admin users.
StaffUser = Annotated[User, Depends(require_roles(UserRole.HR, UserRole.REVIEWER, UserRole.ADMIN))]


@router.get("/departments", response_model=list[DepartmentOut])
def list_departments(db: DbSession, _user: CurrentUser):
    return db.scalars(select(Department).order_by(Department.code)).all()


@router.get("/job-positions", response_model=list[JobPositionOut])
def list_job_positions(db: DbSession, _user: CurrentUser):
    return db.scalars(select(JobPosition).order_by(JobPosition.department_code, JobPosition.id)).all()


@router.get("/job-positions/{position_id}/required-sources", response_model=list[RequiredSourceOut])
def list_required_sources(position_id: str, db: DbSession, _user: StaffUser):
    """Documents the Role Requirement Matrix cites for the position; mandatory ones must be path sources."""
    if db.get(JobPosition, position_id) is None:
        raise AppError(404, "err_job_position", "Unknown job position")
    return role_matrix.required_sources(db, position_id)
