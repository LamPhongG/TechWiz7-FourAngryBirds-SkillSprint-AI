import time
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import CurrentUser, DbSession, require_roles
from app.core.errors import AppError
from app.models import PathPurpose, PathStatus, User, UserRole
from app.schemas.paths import (
    CommentCreate,
    CommentResolve,
    GenerationJobOut,
    PathApprove,
    PathChecksOut,
    PathCreate,
    PathEdit,
    PathOut,
    PathRegenerate,
    PathSubmit,
    PathSummary,
    ReasonBody,
    RequestChanges,
)
from app.services import generation_jobs as jobs
from app.services import paths as service
from app.services.path_checks import check_path
from app.services.path_workflow import ensure_allowed

router = APIRouter(prefix="/paths", tags=["learning paths"])

HrUser = Annotated[User, Depends(require_roles(UserRole.HR))]
ReviewerUser = Annotated[User, Depends(require_roles(UserRole.REVIEWER))]
# Endpoints accessible to staff and admin users.
StaffUser = Annotated[User, Depends(require_roles(UserRole.HR, UserRole.REVIEWER, UserRole.ADMIN))]


@router.get("", response_model=list[PathOut] | list[PathSummary])
def list_paths(
    db: DbSession,
    user: CurrentUser,
    status_filter: Annotated[PathStatus | None, Query(alias="status")] = None,
    purpose: PathPurpose | None = None,
    include_content: bool = False,
):
    """HR: all paths. Reviewer: everything except drafts. Employee: paths published to them.

    include_content=true returns full paths (stages, comments) in one request, for screens that
    compute progress or checks over every path.
    """
    paths = service.list_visible(db, user, status_filter, purpose)
    return service.to_details(db, user, paths) if include_content else service.to_summaries(db, user, paths)


@router.post("", response_model=PathOut, status_code=status.HTTP_201_CREATED)
def create_path(body: PathCreate, db: DbSession, user: HrUser):
    """Create a draft: the server generates it (Pipeline 1), or saves `content` sent by the client (tests, browser draft)."""
    return service.to_detail(db, user, service.create(db, user, body))


@router.post("/jobs", response_model=GenerationJobOut, status_code=status.HTTP_202_ACCEPTED)
def start_create_job(body: PathCreate, user: HrUser):
    """Same as `POST /paths`, but returns at once; poll `GET /paths/jobs/{id}` to follow the run step by step."""
    return _job_out(jobs.start("create", user, lambda db, actor, progress: service.create(db, actor, body, progress)))


@router.get("/jobs/{job_id}", response_model=GenerationJobOut)
def get_job(job_id: str, user: HrUser):
    job = jobs.get(job_id, user)
    if job is None:
        raise AppError(404, "err_job_not_found", "Generation job not found")
    return _job_out(job)


@router.post("/{path_id}/regenerate/jobs", response_model=GenerationJobOut, status_code=status.HTTP_202_ACCEPTED)
def start_regenerate_job(path_id: str, body: PathRegenerate, db: DbSession, user: HrUser):
    # Check visibility and workflow now, so a wrong request fails at once instead of inside the job.
    ensure_allowed(user, "regenerate", service.get_visible(db, user, path_id))
    return _job_out(jobs.start("regenerate", user, lambda db, actor, progress: service.regenerate(
        db, actor, service.get_visible(db, actor, path_id), body, progress)))


def _job_out(job: jobs.Job) -> GenerationJobOut:
    end = job.updated if job.status != "running" else time.time()
    return GenerationJobOut(id=job.id, kind=job.kind, status=job.status, state=job.state, path_id=job.path_id,
                            error=job.error, elapsed_ms=round((end - job.started) * 1000))


@router.get("/{path_id}", response_model=PathOut)
def get_path(path_id: str, db: DbSession, user: CurrentUser):
    return service.to_detail(db, user, service.get_visible(db, user, path_id))


@router.patch("/{path_id}", response_model=PathOut)
def edit_path(path_id: str, body: PathEdit, db: DbSession, user: CurrentUser):
    """Replace the content tree. HR in draft / changes_requested, Reviewer in in_review."""
    path = service.edit(db, user, service.get_visible(db, user, path_id), body)
    return service.to_detail(db, user, path)


@router.delete("/{path_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_path(path_id: str, db: DbSession, user: HrUser):
    """Only drafts can be deleted; the audit trail keeps a record."""
    service.delete(db, user, service.get_visible(db, user, path_id))


@router.post("/{path_id}/regenerate", response_model=PathOut)
def regenerate_path(path_id: str, body: PathRegenerate, db: DbSession, user: HrUser):
    path = service.regenerate(db, user, service.get_visible(db, user, path_id), body)
    return service.to_detail(db, user, path)


@router.post("/{path_id}/submit", response_model=PathOut)
def submit_path(path_id: str, body: PathSubmit, db: DbSession, user: HrUser):
    """Send to review. Resubmitting after requested changes bumps the revision."""
    path = service.submit(db, user, service.get_visible(db, user, path_id), body)
    return service.to_detail(db, user, path)


@router.get("/{path_id}/checks", response_model=PathChecksOut)
def get_path_checks(path_id: str, db: DbSession, user: StaffUser):
    """Server-side verification: knowledge (quotes in sources), flow, injection, coverage → final status."""
    result = check_path(db, service.get_visible(db, user, path_id))
    return PathChecksOut(**result.summary(), items=result.knowledge, flow=result.flow)


@router.get("/{path_id}/comparison")
def get_path_dual_comparison(path_id: str, db: DbSession, user: StaffUser):
    """Dual-pipeline comparison report against ground truth requirements."""
    from app.comparator.engine import compare_path_with_ground_truth
    path = service.get_visible(db, user, path_id)
    return compare_path_with_ground_truth(db, path)


@router.post("/{path_id}/request-changes", response_model=PathOut)
def request_changes(path_id: str, body: RequestChanges, db: DbSession, user: ReviewerUser):
    """Send back to HR with feedback (at least 10 characters)."""
    path = service.request_changes(db, user, service.get_visible(db, user, path_id), body)
    return service.to_detail(db, user, path)


@router.post("/{path_id}/approve", response_model=PathOut)
def approve_path(path_id: str, body: PathApprove, db: DbSession, user: ReviewerUser):
    """Publish to departments and/or job positions. Blocked while server checks find blocking problems."""
    path = service.approve(db, user, service.get_visible(db, user, path_id), body)
    return service.to_detail(db, user, path)


@router.post("/{path_id}/archive", response_model=PathOut)
def archive_path(path_id: str, body: ReasonBody, db: DbSession, user: CurrentUser):
    """Withdraw a published path (reason required). Employees keep their progress."""
    path = service.archive(db, user, service.get_visible(db, user, path_id), body.reason)
    return service.to_detail(db, user, path)


@router.post("/{path_id}/comments", response_model=PathOut, status_code=status.HTTP_201_CREATED)
def add_comment(path_id: str, body: CommentCreate, db: DbSession, user: CurrentUser):
    path = service.add_comment(db, user, service.get_visible(db, user, path_id), body)
    return service.to_detail(db, user, path)


@router.post("/{path_id}/comments/{comment_id}/resolve", response_model=PathOut)
def resolve_comment(path_id: str, comment_id: str, body: CommentResolve, db: DbSession, user: CurrentUser):
    path = service.resolve_comment(db, user, service.get_visible(db, user, path_id), comment_id, body.resolved)
    return service.to_detail(db, user, path)
