"""Learning-path operations. Every change checks the workflow table, then saves the path and its
audit row in one commit (same contract as frontend `contexts/PathsContext.jsx`)."""
from dataclasses import dataclass
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.config import get_settings
from app.core.errors import AppError
from app.core.injection_filter import scan_chunks
from app.db.base import new_id, utcnow
from app.genai_pipeline.client import get_llm_client
from app.genai_pipeline.generator import Progress, _silent, generate_content
from app.genai_pipeline.local_draft import NoContentError
from app.genai_pipeline.types import DEFAULT_ONBOARDING_DAYS, GenerationRequest, RoleScope, SourceDoc
from app.ingestion.chunker import outline
from app.ingestion.extract import ExtractionError, extract
from app.models import (
    Department,
    Document,
    DocumentChunk,
    FinalStatus,
    InjectionFlag,
    JobPosition,
    LearningPath,
    PathAssignment,
    PathComment,
    PathLevel,
    PathPurpose,
    PathSource,
    PathStatus,
    ProcessingStatus,
    RoleRequirement,
    User,
    UserRole,
)
from app.schemas.paths import (
    MIN_REASON_LENGTH,
    Actor,
    Approval,
    CommentCreate,
    CommentOut,
    PathApprove,
    PathContent,
    PathCreate,
    PathEdit,
    PathOut,
    PathRegenerate,
    PathSubmit,
    PathSummary,
    PublishedTo,
    RequestChanges,
    SourceOut,
    Stage,
    Target,
)
from app.services import audit, documents, enrollments, role_matrix
from app.services.path_checks import check_path
from app.services.path_workflow import allowed_actions, check_stage_keys, ensure_allowed
from app.services.visibility import path_filter

TITLES = {
    PathPurpose.ONBOARDING: ("Onboarding", "Onboarding"),
    PathPurpose.PROMOTION: ("Promotion upskilling", "Promotion upskilling"),
}

_WITH_RELATIONS = (
    selectinload(LearningPath.sources),
    selectinload(LearningPath.assignments),
    selectinload(LearningPath.comments),
)


def get_visible(db: Session, user: User, path_id: str) -> LearningPath:
    """404 (not 403) for paths the user cannot see, so their existence is not leaked."""
    path = db.scalar(select(LearningPath).options(*_WITH_RELATIONS).where(LearningPath.id == path_id, path_filter(user)))
    if path is None:
        raise AppError(404, "err_path_not_found", "Learning path not found")
    return path


def list_visible(db: Session, user: User, status: PathStatus | None, purpose: PathPurpose | None) -> list[LearningPath]:
    stmt = select(LearningPath).options(*_WITH_RELATIONS).where(path_filter(user)).order_by(LearningPath.updated_at.desc())
    if status:
        stmt = stmt.where(LearningPath.status == status)
    if purpose:
        stmt = stmt.where(LearningPath.purpose == purpose)
    return list(db.scalars(stmt))


def create(db: Session, actor: User, body: PathCreate, progress: Progress | None = None) -> LearningPath:
    """Create a draft. Without body.content the server generates it from the sources (Pipeline 1).

    `progress` follows the run step by step (sources → … → saving), for `services.generation_jobs`.
    """
    emit = progress or _silent
    ensure_hr(actor)
    position = db.get(JobPosition, body.job_position_id)
    if position is None:
        raise AppError(422, "err_job_position", "Unknown job position")
    prompt = _checked_prompt(body.prompt)
    docs = _ready_sources(db, body.source_document_ids)
    gaps = _check_mandatory_sources(db, position.id, docs, body.allow_missing_mandatory)
    emit("sources", count=len(docs), codes=[d.code for d in docs], mandatory_unavailable=gaps.unavailable,
         mandatory_omitted=gaps.omitted)
    duration = (body.duration_days or DEFAULT_ONBOARDING_DAYS) if body.purpose == PathPurpose.ONBOARDING else None
    path_id = new_id("LP")
    content = body.content or _generate(db, path_id, body.purpose, body.level, position, docs, prompt, body.language,
                                        duration, emit)
    check_stage_keys(body.purpose, [s.key for s in content.stages], duration)

    vi, en = TITLES[body.purpose]
    path = LearningPath(
        id=path_id,
        title=f"{en} — {position.name_en or position.name}",
        title_en=f"{en} — {position.name_en or position.name}",
        purpose=body.purpose,
        level=body.level,
        target_job_position_id=position.id,
        target_department_code=position.department_code,
        duration_days=duration,
        prompt=prompt,
        status=PathStatus.DRAFT,
        revision=1,
        created_by_id=actor.id,
    )
    _apply_content(path, content, gaps)
    # Pipeline 2 independently computes coverage — does not rely on client/AI-supplied content.coverage.
    path.coverage = role_matrix.compute_coverage(db, path.stages, position.id)
    path.sources = _source_rows(docs)
    db.add(path)
    audit.record(db, actor, "generate", path, status_before=None, status_after=PathStatus.DRAFT,
                 details=_generation_details(path, docs, gaps))
    emit("saving")
    db.commit()
    return path


def regenerate(db: Session, actor: User, path: LearningPath, body: PathRegenerate,
               progress: Progress | None = None) -> LearningPath:
    """Replace content from (possibly newer) sources. Comments and history are kept.

    Regeneration steps:
    1. Check missing requirements flagged from previous evaluation.
    2. Auto-include required documents if requested.
    3. Include missing requirements in generation prompt for coverage.
    4. Re-evaluate coverage score on the new draft.
    """
    emit = progress or _silent
    ensure_allowed(actor, "regenerate", path)
    if body.prompt is not None:
        path.prompt = _checked_prompt(body.prompt)
    docs = _ready_sources(db, body.source_document_ids)

    # 1. Detect missing requirements from previous evaluation
    prev_coverage = path.coverage or role_matrix.compute_coverage(db, path.stages, path.target_job_position_id)
    missing_req_ids = prev_coverage.get("missing", []) if prev_coverage else []

    # 2. Auto-include missing approved documents from repository if requested
    auto_added_codes: list[str] = []
    missing_req_objects: list[RoleRequirement] = []
    if missing_req_ids:
        missing_req_objects = db.scalars(
            select(RoleRequirement).where(RoleRequirement.id.in_(missing_req_ids))
        ).all()
        if body.auto_include_missing:
            existing_doc_ids = {d.id for d in docs}
            existing_doc_codes = {d.code for d in docs}
            needed_doc_codes = {r.source_doc_code for r in missing_req_objects if r.source_doc_code}

            for code in sorted(needed_doc_codes):
                if code not in existing_doc_codes:
                    candidates = db.scalars(
                        select(Document).where(
                            Document.code == code,
                            Document.processing_status == ProcessingStatus.READY,
                        )
                    ).all()
                    if candidates:
                        families = db.scalars(select(Document).where(Document.family.in_({d.family for d in candidates}))).all()
                        lifecycle = documents.compute_lifecycle(list(families), date.today())
                        approved_doc = next((d for d in candidates if lifecycle.get(d.id, ("", ""))[0] == "active"), candidates[0])
                        if approved_doc and approved_doc.id not in existing_doc_ids:
                            docs.append(approved_doc)
                            existing_doc_ids.add(approved_doc.id)
                            existing_doc_codes.add(approved_doc.code)
                            auto_added_codes.append(approved_doc.code)

    gaps = _check_mandatory_sources(db, path.target_job_position_id, docs, body.allow_missing_mandatory)
    emit("sources", count=len(docs), codes=[d.code for d in docs], mandatory_unavailable=gaps.unavailable,
         mandatory_omitted=gaps.omitted)

    # 3. Add focused feedback prompt so GenAI targets the missing requirements explicitly
    effective_prompt = path.prompt
    if missing_req_objects:
        feedback_lines = []
        for r in missing_req_objects:
            sec = f" §{r.source_section}" if r.source_section else ""
            prio = r.priority.value if hasattr(r.priority, "value") else str(r.priority)
            desc = r.policy_requirement or r.process_requirement or r.competency or "Mandatory requirement"
            feedback_lines.append(f"- Requirement {r.id}: {r.source_doc_code}{sec} ({prio}) — {desc}")
        feedback_block = (
            "\n\n[INDEPENDENT VALIDATION FEEDBACK - TARGET MISSING REQUIREMENTS]:\n"
            "The Python validation pipeline flagged that previous attempts missed the following mandatory requirements.\n"
            "You MUST generate dedicated lessons/tasks/quiz questions explicitly covering and citing these exact sections:\n"
            + "\n".join(feedback_lines)
        )
        effective_prompt = (effective_prompt or "") + feedback_block

    content = body.content or _generate(db, path.id, path.purpose, path.level, db.get(JobPosition, path.target_job_position_id),
                                        docs, effective_prompt, body.language, path.duration_days, emit)
    check_stage_keys(path.purpose, [s.key for s in content.stages], path.duration_days)
    _apply_content(path, content, gaps)

    # 4. Recompute coverage with rule engine on updated content
    path.coverage = role_matrix.compute_coverage(db, path.stages, path.target_job_position_id)
    path.sources = _source_rows(docs)

    details = _generation_details(path, docs, gaps)
    if auto_added_codes:
        details["auto_added_sources"] = ", ".join(auto_added_codes)
    if missing_req_ids:
        details["targeted_missing_requirements"] = str(len(missing_req_ids))

    audit.record(db, actor, "regenerate", path, status_before=path.status, status_after=path.status,
                 details=details)
    emit("saving")
    db.commit()
    return path


def edit(db: Session, actor: User, path: LearningPath, body: PathEdit) -> LearningPath:
    ensure_allowed(actor, "edit", path)
    check_stage_keys(path.purpose, [s.key for s in body.stages], path.duration_days)
    path.stages = _dump_stages(body.stages)
    # Manual HR edits may add/remove citations → recompute coverage instead of preserving old score.
    path.coverage = role_matrix.compute_coverage(db, path.stages, path.target_job_position_id)
    audit.record(db, actor, "edit", path, status_before=path.status, status_after=path.status, details=body.details)
    db.commit()
    return path


def submit(db: Session, actor: User, path: LearningPath, body: PathSubmit) -> LearningPath:
    ensure_allowed(actor, "submit", path)
    before = path.status
    resubmit = before is PathStatus.CHANGES_REQUESTED
    if resubmit:
        path.revision += 1
    path.status = PathStatus.IN_REVIEW
    path.submitted_at = utcnow()
    note = _clean(body.note)
    if note:
        path.comments.append(PathComment(id=new_id("CMT"), author_id=actor.id, text=note))
    checks = check_path(db, path)
    audit.record(db, actor, "resubmit" if resubmit else "submit", path, status_before=before,
                 status_after=PathStatus.IN_REVIEW, final_status=checks.final_status, reason=note)
    db.commit()
    return path


def request_changes(db: Session, actor: User, path: LearningPath, body: RequestChanges) -> LearningPath:
    """Reviewer sends the path back to HR with mandatory feedback."""
    ensure_allowed(actor, "request_changes", path)
    before = path.status
    path.status = PathStatus.CHANGES_REQUESTED
    path.comments.append(PathComment(id=new_id("CMT"), author_id=actor.id, text=body.message))
    checks = check_path(db, path)
    audit.record(db, actor, "request_changes", path, status_before=before, status_after=PathStatus.CHANGES_REQUESTED,
                 final_status=checks.final_status, reason=body.message)
    db.commit()
    return path


def approve(db: Session, actor: User, path: LearningPath, body: PathApprove) -> LearningPath:
    """Reviewer publishes the path to departments and/or job positions.

    The server re-runs every check: blocking problems (knowledge errors, injection in content, broken
    structure) forbid publishing even with a reason; any other non-verified verdict needs a reason.
    """
    ensure_allowed(actor, "approve", path)
    checks = check_path(db, path)
    if checks.blocking:
        raise AppError(409, "err_approve_blocked", "Blocking problems must be fixed before publishing",
                       reasons=", ".join(r["key"] for r in checks.reasons))
    reason = _clean(body.reason)
    if checks.final_status is not FinalStatus.VERIFIED and (reason is None or len(reason) < MIN_REASON_LENGTH):
        raise AppError(422, "err_reason_required", "A reason is required to publish a path that is not fully verified",
                       n=MIN_REASON_LENGTH)
    departments = list(dict.fromkeys(body.departments))
    positions = list(dict.fromkeys(body.job_positions))
    if not departments and not positions:
        raise AppError(422, "err_publish_target", "Choose at least one department or job position")
    unknown = ([d for d in departments if db.get(Department, d) is None]
               + [p for p in positions if db.get(JobPosition, p) is None])
    if unknown:
        raise AppError(422, "err_publish_target", f"Unknown target: {', '.join(unknown)}")

    before = path.status
    now = utcnow()
    path.status = PathStatus.PUBLISHED
    path.published_at = now
    path.approved_by_id = actor.id
    path.approval_final_status = checks.final_status
    path.approval_reason = reason
    path.assignments = ([PathAssignment(department_code=d) for d in departments]
                        + [PathAssignment(job_position_id=p) for p in positions])
    audit.record(db, actor, "approve", path, status_before=before, status_after=PathStatus.PUBLISHED,
                 final_status=checks.final_status, reason=reason,
                 details={"departments": ", ".join(departments), "roles": ", ".join(positions)})
    enrollments.assign_published_path(db, path, actor)
    db.commit()
    return path


def archive(db: Session, actor: User, path: LearningPath, reason: str) -> LearningPath:
    ensure_allowed(actor, "archive", path)
    before = path.status
    path.status = PathStatus.ARCHIVED
    path.archived_at = utcnow()
    enrollments.withdraw_for_archived_path(db, path)
    audit.record(db, actor, "archive", path, status_before=before, status_after=PathStatus.ARCHIVED, reason=reason)
    db.commit()
    return path


def delete(db: Session, actor: User, path: LearningPath) -> None:
    ensure_allowed(actor, "delete", path)
    audit.record(db, actor, "delete", path, status_before=path.status, status_after=None)
    db.delete(path)
    db.commit()


def add_comment(db: Session, actor: User, path: LearningPath, body: CommentCreate) -> LearningPath:
    ensure_allowed(actor, "comment", path)
    if body.reply_to and not any(c.id == body.reply_to for c in path.comments):
        raise AppError(422, "err_comment_not_found", "The comment being replied to is not on this path")
    item_ref = body.item_ref.model_dump() if body.item_ref else None
    path.comments.append(PathComment(id=new_id("CMT"), author_id=actor.id, text=body.text,
                                     item_ref=item_ref, reply_to_id=body.reply_to))
    audit.record(db, actor, "comment", path, status_before=path.status, status_after=path.status, reason=body.text,
                 details={"item": item_ref["id"]} if item_ref else None)
    db.commit()
    return path


def resolve_comment(db: Session, actor: User, path: LearningPath, comment_id: str, resolved: bool) -> LearningPath:
    ensure_allowed(actor, "comment", path)
    comment = next((c for c in path.comments if c.id == comment_id), None)
    if comment is None:
        raise AppError(404, "err_comment_not_found", "Comment not found")
    comment.resolved = resolved
    comment.resolved_by_id = actor.id if resolved else None
    # Resolving is bookkeeping on the discussion, not a change to the path: no audit row (as in the frontend).
    db.commit()
    return path


def ensure_hr(actor: User) -> None:
    if actor.user_role is not UserRole.HR:
        raise AppError(403, "err_action_not_allowed", "Only HR can create learning paths")


def _clean(text: str | None) -> str | None:
    text = (text or "").strip()
    return text or None


def _checked_prompt(text: str | None) -> str | None:
    """HR's extra instructions go into the model prompt, so they get the same injection screening as documents."""
    prompt = _clean(text)
    if prompt and scan_chunks([{"chunk_id": "prompt", "page": None, "content": prompt}]):
        raise AppError(422, "err_prompt_injection", "The extra instructions contain a prompt-injection pattern")
    return prompt


@dataclass
class MandatoryGaps:
    # Ready in the repository but left out by HR (allowed only with `allow_missing_mandatory`).
    omitted: list[str]
    # Not selectable yet: not uploaded, still processing, or only an outdated version on file.
    unavailable: list[str]


def _check_mandatory_sources(db: Session, position_id: str, docs: list[Document], allow_missing: bool) -> MandatoryGaps:
    """Mandatory documents of the Role Requirement Matrix (SRS Step 10, 28) that the sources do not cover.

    Leaving out a ready one is refused unless HR confirmed it; either way the gap is recorded and the checks
    warn the Reviewer (`reason_mandatory_sources_missing`).
    """
    omitted, unavailable = role_matrix.missing_mandatory_sources(db, position_id, {d.id for d in docs})
    if omitted and not allow_missing:
        raise AppError(422, "err_mandatory_sources", "Mandatory documents of the Role Requirement Matrix are missing",
                       codes=", ".join(omitted))
    return MandatoryGaps(omitted, unavailable)


def _generation_details(path: LearningPath, docs: list[Document], gaps: MandatoryGaps) -> dict[str, str]:
    details = {"engine": path.engine, "sources": ", ".join(d.code for d in docs)}
    if path.duration_days:
        details["duration_days"] = str(path.duration_days)
    if gaps.unavailable:
        details["mandatory_unavailable"] = ", ".join(gaps.unavailable)
    if gaps.omitted:
        details["mandatory_omitted"] = ", ".join(gaps.omitted)
    return details


def _generate(db: Session, path_id: str, purpose: PathPurpose, level: PathLevel, position: JobPosition,
              docs: list[Document], prompt: str | None, language: str, duration_days: int | None,
              progress: Progress | None = None) -> PathContent:
    chunk_rows = db.scalars(select(DocumentChunk).where(DocumentChunk.document_id.in_([d.id for d in docs]))
                            .order_by(DocumentChunk.document_id, DocumentChunk.position))
    flag_rows = db.scalars(select(InjectionFlag).where(InjectionFlag.document_id.in_([d.id for d in docs])))
    chunks: dict[str, list[dict]] = {}
    for c in chunk_rows:
        chunks.setdefault(c.document_id, []).append(
            {"chunk_id": c.chunk_id, "section_id": c.section_id, "heading": c.heading, "page": c.page, "content": c.content})
    flags: dict[str, list[dict]] = {}
    for f in flag_rows:
        flags.setdefault(f.document_id, []).append({"chunk_id": f.chunk_id, "rule_id": f.rule_id})

    sources = [SourceDoc(id=d.id, code=d.code, version=d.version, title=d.title, title_en=d.title_en, category=d.category,
                         department=d.department_code, chunks=chunks.get(d.id, []), flags=flags.get(d.id, []),
                         outline=_outline(d))
               for d in docs]
    req = GenerationRequest(path_id=path_id, purpose=purpose.value, level=level.value, role_name=position.name,
                            role_name_en=position.name_en, department=position.department_code,
                            prompt_version=get_settings().prompt_version, language=language, hr_prompt=prompt,
                            duration_days=duration_days,
                            requirements=[role_matrix.as_generation_dict(r)
                                          for r in role_matrix.requirements_for(db, position.id)],
                            scope=_role_scope(db, position))
    try:
        result = generate_content(req, sources, get_llm_client(), progress)
    except NoContentError:
        raise AppError(422, "err_no_content", "None of the selected documents has usable text") from None
    return PathContent(stages=result.stages, excluded_chunks=result.excluded_chunks, coverage=None,
                       engine=result.engine, model=result.model, prompt_version=result.prompt_version,
                       generation=result.report)


def _role_scope(db: Session, position: JobPosition) -> RoleScope:
    positions = db.scalars(select(JobPosition)).all()
    departments = db.scalars(select(Department.code)).all()
    return RoleScope(role=position.name_en, department=position.department_code,
                     other_roles=[p.name_en for p in positions if p.id != position.id],
                     other_departments=[d for d in departments if d not in (position.department_code, "Company-wide")])


def _outline(doc: Document) -> list[str]:
    """All headings of the stored file, parents included. Chunks keep only their nearest heading, so the role filter
    needs this to see which job a subsection belongs to. A missing or unreadable file only disables that filtering."""
    if doc.ext == "csv":
        return []
    try:
        return outline(extract(documents.file_location(doc).read_bytes(), doc.ext).blocks)
    except (AppError, ExtractionError, OSError):
        return []


def _dump_stages(stages: list[Stage]) -> list[dict]:
    return [s.model_dump(mode="json") for s in stages]


def _apply_content(path: LearningPath, content: PathContent, gaps: MandatoryGaps) -> None:
    path.stages = _dump_stages(content.stages)
    path.excluded_chunks = [c.model_dump(mode="json") for c in content.excluded_chunks]
    path.coverage = content.coverage
    path.engine = content.engine
    path.model = content.model
    path.prompt_version = content.prompt_version
    path.generation = content.generation
    if path.generation is not None and gaps.unavailable:
        path.generation = {**path.generation, "mandatory_unavailable": gaps.unavailable}
    if path.generation is not None and gaps.omitted:
        path.generation = {**path.generation, "mandatory_omitted": gaps.omitted}


def _ready_sources(db: Session, doc_ids: list[str]) -> list[Document]:
    """Sources in the order HR picked them; each must exist and be fully processed."""
    unique_ids = list(dict.fromkeys(doc_ids))
    docs = {d.id: d for d in db.scalars(select(Document).where(Document.id.in_(unique_ids)))}
    missing = [i for i in unique_ids if i not in docs]
    if missing:
        raise AppError(422, "err_source_missing", "Source document not found", ids=", ".join(missing))
    not_ready = [docs[i].code for i in unique_ids if docs[i].processing_status is not ProcessingStatus.READY]
    if not_ready:
        raise AppError(409, "err_source_not_ready", "Source document is not processed yet", codes=", ".join(not_ready))
    return [docs[i] for i in unique_ids]


def _source_rows(docs: list[Document]) -> list[PathSource]:
    return [PathSource(document_id=d.id, doc_code=d.code, doc_version=d.version, position=i) for i, d in enumerate(docs)]


class _Lookups:
    """Users and source documents for a batch of paths, loaded with two queries."""

    def __init__(self, db: Session, paths: list[LearningPath]):
        user_ids = set()
        doc_ids = set()
        for p in paths:
            user_ids.update(filter(None, [p.created_by_id, p.approved_by_id]))
            for c in p.comments:
                user_ids.update(filter(None, [c.author_id, c.resolved_by_id]))
            doc_ids.update(s.document_id for s in p.sources if s.document_id)
        self.users = {u.id: u for u in db.scalars(select(User).where(User.id.in_(user_ids)))} if user_ids else {}
        self.docs = {d.id: d for d in db.scalars(select(Document).where(Document.id.in_(doc_ids)))} if doc_ids else {}

    def actor(self, user_id: str | None) -> Actor | None:
        user = self.users.get(user_id) if user_id else None
        return Actor(id=user.id, name=user.name, role=user.user_role) if user else None

    def source(self, s: PathSource) -> SourceOut:
        doc = self.docs.get(s.document_id) if s.document_id else None
        return SourceOut(document_id=s.document_id, code=s.doc_code, version=s.doc_version,
                         title=doc.title if doc else None, title_en=doc.title_en if doc else None)


def _summary_fields(p: LearningPath, user: User, look: _Lookups) -> dict:
    published_to = None
    if p.assignments:
        published_to = PublishedTo(
            departments=[a.department_code for a in p.assignments if a.department_code],
            job_positions=[a.job_position_id for a in p.assignments if a.job_position_id],
        )
    return {
        "id": p.id,
        "title": p.title,
        "title_en": p.title_en,
        "purpose": p.purpose,
        "level": p.level,
        "duration_days": p.duration_days,
        "target": Target(job_position_id=p.target_job_position_id, department_code=p.target_department_code),
        "status": p.status,
        "revision": p.revision,
        "engine": p.engine,
        "prompt_version": p.prompt_version,
        "coverage": p.coverage,
        "sources": [look.source(s) for s in p.sources],
        "module_count": sum(len(stage.get("modules", [])) for stage in p.stages),
        "open_comment_count": sum(1 for c in p.comments if not c.resolved),
        "published_to": published_to,
        "created_by": look.actor(p.created_by_id),
        "created_at": p.created_at,
        "updated_at": p.updated_at,
        "submitted_at": p.submitted_at,
        "published_at": p.published_at,
        "archived_at": p.archived_at,
        "allowed_actions": allowed_actions(user, p),
    }


def to_summaries(db: Session, user: User, paths: list[LearningPath]) -> list[PathSummary]:
    look = _Lookups(db, paths)
    return [PathSummary(**_summary_fields(p, user, look)) for p in paths]


def to_detail(db: Session, user: User, path: LearningPath) -> PathOut:
    return to_details(db, user, [path])[0]


def to_details(db: Session, user: User, paths: list[LearningPath]) -> list[PathOut]:
    look = _Lookups(db, paths)
    return [_detail(path, user, look) for path in paths]


def _detail(path: LearningPath, user: User, look: _Lookups) -> PathOut:
    approval = None
    if path.approved_by_id:
        approval = Approval(by=look.actor(path.approved_by_id), at=path.published_at,
                            final_status=path.approval_final_status, reason=path.approval_reason)
    comments = [
        CommentOut(id=c.id, author=look.actor(c.author_id), at=c.created_at, text=c.text, item_ref=c.item_ref,
                   reply_to=c.reply_to_id, resolved=c.resolved, resolved_by=look.actor(c.resolved_by_id))
        for c in path.comments
    ]
    return PathOut(
        **_summary_fields(path, user, look),
        prompt=path.prompt,
        model=path.model,
        generation=path.generation,
        stages=path.stages,
        excluded_chunks=path.excluded_chunks,
        comments=comments,
        approval=approval,
    )
