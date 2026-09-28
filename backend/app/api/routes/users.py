"""User management endpoints for Admin (SRS Section 1.6 & Step 51).

Supports full CRUD:
- Create new user accounts
- View users with role/department filtering and search
- Update user metadata
- Soft delete: deactivates account (is_active=False) preserving audit trail and database records
- Reactivate deactivated users
- Create an employee account from a CV: the profile is read in Python, checked by the Admin, and the generated
  password is emailed to the employee
"""
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import or_, select
from sqlalchemy.orm import selectinload

from app.api.deps import DbSession, require_roles
from app.core import email
from app.core.config import get_settings
from app.core.errors import AppError
from app.core.security import generate_password, hash_password
from app.db.base import new_id
from app.ingestion.extract import ExtractionError
from app.ingestion.validation import FileRejected, check_file, file_extension
from app.models import Department, JobPosition, User, UserRole
from app.schemas.auth import UserOut
from app.schemas.users import CvDraft, EmployeeOnboard, OnboardResult, UserCreate, UserStatusResponse, UserUpdate
from app.services import cv_parser, enrollments

router = APIRouter(prefix="/users", tags=["user management"])

AdminUser = Annotated[User, Depends(require_roles(UserRole.ADMIN, UserRole.HR))]


def _ensure_can_manage(actor: User, *roles: UserRole) -> None:
    """HR onboards employees; only an Admin may create, change or deactivate staff and admin accounts.

    Without this an HR account could create an admin account, or promote itself, and take over the system.
    """
    if actor.user_role is not UserRole.ADMIN and any(r is not UserRole.EMPLOYEE for r in roles):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only an administrator can manage staff accounts")


@router.get("", response_model=list[UserOut])
def list_users(
    db: DbSession,
    user: AdminUser,
    search: str | None = None,
    role: UserRole | None = None,
    department_code: str | None = None,
    is_active: bool | None = None,
):
    """List all user accounts with search and role/department filtering."""
    stmt = select(User).options(selectinload(User.job_position)).order_by(User.created_at.desc())

    if search:
        pattern = f"%{search.strip().lower()}%"
        stmt = stmt.where(or_(User.email.ilike(pattern), User.name.ilike(pattern)))
    if role:
        stmt = stmt.where(User.user_role == role)
    if department_code:
        stmt = stmt.where(User.department_code == department_code)
    if is_active is not None:
        stmt = stmt.where(User.is_active == is_active)

    users = db.scalars(stmt).all()
    return [UserOut.from_user(u) for u in users]


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(
    body: UserCreate,
    db: DbSession,
    actor: AdminUser,
):
    """Create a user account. HR may create employee accounts only."""
    _ensure_can_manage(actor, body.user_role)
    # Check if email exists
    existing = db.scalar(select(User).where(User.email == body.email.lower().strip()))
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Email '{body.email}' is already registered in the system.",
        )

    # Validate department if provided
    if body.department_code:
        dept = db.get(Department, body.department_code)
        if not dept:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Department code '{body.department_code}' does not exist.",
            )

    # Validate job position if provided
    if body.job_position_id:
        pos = db.get(JobPosition, body.job_position_id)
        if not pos:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Job position '{body.job_position_id}' does not exist.",
            )

    user = User(
        id=new_id("USR"),
        email=body.email.lower().strip(),
        name=body.name.strip(),
        password_hash=hash_password(body.password),
        user_role=body.user_role,
        job_title=body.job_title.strip() if body.job_title else None,
        department_code=body.department_code,
        job_position_id=body.job_position_id,
        is_active=True,
        # Chosen by the Admin, not by the person who will use the account.
        password_is_temporary=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return UserOut.from_user(user)


CV_EXTENSIONS = ("pdf", "docx", "txt", "md")


@router.post("/cv/parse", response_model=CvDraft)
async def parse_cv(actor: AdminUser, file: Annotated[UploadFile, File()]) -> CvDraft:
    """Read name, email, experience and skills from a CV (pdf, docx, txt, md). The file is not stored.

    Contact details other than the email, the address, date of birth and ID numbers are not read (SRS Step 9).
    """
    _ensure_can_manage(actor, UserRole.EMPLOYEE)
    max_bytes = get_settings().max_upload_mb * 1024 * 1024
    content = await file.read(max_bytes + 1)
    ext = file_extension(file.filename or "")
    if ext not in CV_EXTENSIONS:
        raise AppError(415, "err_file_type", f"Unsupported CV type: {ext}", ext=ext or "?",
                       list=", ".join(f".{e}" for e in CV_EXTENSIONS))
    try:
        check_file(content, ext, max_bytes)
        draft = cv_parser.parse_cv(content, ext)
    except FileRejected as exc:
        raise AppError(413 if exc.code == "err_file_too_large" else 422, exc.code, f"File rejected: {exc.code}",
                       **exc.params) from None
    except ExtractionError as exc:
        raise AppError(422, "err_cv_unreadable", f"CV could not be read: {exc.code}", reason=exc.code) from None
    return CvDraft(**draft)


@router.post("/from-cv", response_model=OnboardResult, status_code=status.HTTP_201_CREATED)
def create_from_cv(body: EmployeeOnboard, db: DbSession, actor: AdminUser) -> OnboardResult:
    """Create an employee account, assign the onboarding paths of the position and email the login details.

    The password is generated here and only its hash is stored. It is returned in the response only when the email
    could not be sent, so the Admin can hand it over another way.
    """
    _ensure_can_manage(actor, UserRole.EMPLOYEE)
    user_email = body.email.lower().strip()
    if db.scalar(select(User.id).where(User.email == user_email)) is not None:
        raise AppError(409, "err_email_taken", "An account with this email already exists")
    position = db.get(JobPosition, body.job_position_id)
    if position is None:
        raise AppError(422, "err_position_unknown", "Unknown job position")

    password = generate_password()
    user = User(
        id=new_id("USR"),
        email=user_email,
        name=body.name.strip(),
        password_hash=hash_password(password),
        password_is_temporary=True,
        user_role=UserRole.EMPLOYEE,
        job_position_id=position.id,
        department_code=position.department_code,
        experience_level=body.experience_level,
        previous_experience=(body.previous_experience or "").strip() or None,
        competencies=[c.strip() for c in body.competencies if c.strip()],
    )
    db.add(user)
    db.flush()
    enrollments.assign_onboarding_to(db, user)
    db.commit()
    db.refresh(user)

    sent = email.send_account_credentials(
        to_email=user_email,
        name=user.name,
        password=password,
        login_url=f"{get_settings().frontend_url}/login",
        position_name=position.name,
        department_name=position.department.name,
    )
    return OnboardResult(user=UserOut.from_user(user), email_sent=sent, temporary_password=None if sent else password)


@router.get("/{user_id}", response_model=UserOut)
def get_user(
    user_id: str,
    db: DbSession,
    user: AdminUser,
):
    """Get single user profile by id."""
    target = db.scalar(
        select(User).options(selectinload(User.job_position)).where(User.id == user_id)
    )
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return UserOut.from_user(target)


@router.patch("/{user_id}", response_model=UserOut)
def update_user(
    user_id: str,
    body: UserUpdate,
    db: DbSession,
    actor: AdminUser,
):
    """Update user information. HR may edit employee accounts only, and cannot change anyone's role to staff."""
    target = db.scalar(
        select(User).options(selectinload(User.job_position)).where(User.id == user_id)
    )
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    _ensure_can_manage(actor, target.user_role, body.user_role or target.user_role)

    old_dept = target.department_code
    old_pos = target.job_position_id

    if body.name is not None:
        target.name = body.name.strip()
    if body.user_role is not None:
        target.user_role = body.user_role
    if body.job_title is not None:
        target.job_title = body.job_title.strip() or None
    if body.department_code is not None:
        if body.department_code:
            dept = db.get(Department, body.department_code)
            if not dept:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Department code '{body.department_code}' does not exist.",
                )
        target.department_code = body.department_code or None
    if body.job_position_id is not None:
        if body.job_position_id:
            pos = db.get(JobPosition, body.job_position_id)
            if not pos:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Job position '{body.job_position_id}' does not exist.",
                )
            if not body.department_code:
                target.department_code = pos.department_code
            if not body.job_title:
                target.job_title = pos.name_en
        target.job_position_id = body.job_position_id or None
    if body.password:
        target.password_hash = hash_password(body.password)
        target.password_is_temporary = True

    dept_changed = target.department_code != old_dept
    pos_changed = target.job_position_id != old_pos
    if (dept_changed or pos_changed) and target.user_role == UserRole.EMPLOYEE:
        enrollments.sync_enrollments_on_user_transfer(db, target, actor)

    db.commit()
    db.refresh(target)
    return UserOut.from_user(target)


@router.delete("/{user_id}", response_model=UserStatusResponse)
def soft_delete_user(
    user_id: str,
    db: DbSession,
    actor: AdminUser,
):
    """Soft delete user: deactivates account (is_active=False) preserving database records and audit history."""
    if actor.id == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot deactivate your own account.",
        )

    target = db.scalar(
        select(User).options(selectinload(User.job_position)).where(User.id == user_id)
    )
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    _ensure_can_manage(actor, target.user_role)

    target.is_active = False
    db.commit()
    db.refresh(target)
    return UserStatusResponse(
        success=True,
        message=f"Account {target.name} ({target.email}) has been deactivated safely in the database.",
        user=UserOut.from_user(target),
    )


@router.post("/{user_id}/restore", response_model=UserStatusResponse)
def restore_user(
    user_id: str,
    db: DbSession,
    actor: AdminUser,
):
    """Reactivate a previously deactivated user account."""
    target = db.scalar(
        select(User).options(selectinload(User.job_position)).where(User.id == user_id)
    )
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    _ensure_can_manage(actor, target.user_role)

    target.is_active = True
    db.commit()
    db.refresh(target)
    return UserStatusResponse(
        success=True,
        message=f"Account {target.name} ({target.email}) has been reactivated successfully.",
        user=UserOut.from_user(target),
    )

