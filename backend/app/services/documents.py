"""Document repository: upload with validation, processing into chunks, lifecycle, deletion."""
import hashlib
import mimetypes
from datetime import date
from functools import cmp_to_key
from pathlib import Path

from sqlalchemy import delete, func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import AppError
from app.db.base import new_id, utcnow
from app.ingestion.extract import ExtractionError
from app.ingestion.pipeline import ENGINE, process_file
from app.ingestion.validation import FileRejected, check_file, compare_versions, file_extension
from app.models import (
    Department,
    Document,
    DocumentChunk,
    InjectionFlag,
    LearningPath,
    PathSource,
    PathStatus,
    ProcessingStatus,
    User,
)
from app.schemas.documents import DocumentMeta, DocumentOut
from app.services.document_catalog import family_of, vietnamese_title
from app.services.visibility import document_filter

# A document still under review or already taught must keep its file: citations open it by page.
_PATH_STATUSES_LOCKING_SOURCES = (PathStatus.IN_REVIEW, PathStatus.CHANGES_REQUESTED, PathStatus.PUBLISHED)


def _file_path(doc: Document) -> Path:
    return get_settings().upload_dir / doc.storage_path


def get_visible(db: Session, user: User, doc_id: str) -> Document:
    doc = db.scalar(select(Document).where(Document.id == doc_id, document_filter(user)))
    if doc is None:
        raise AppError(404, "err_document_not_found", "Document not found")
    return doc


def compute_lifecycle(docs: list[Document], today: date) -> dict[str, tuple[str, str | None]]:
    """Map document id → (status, superseded_by_id). Port of frontend `computeLifecycle`.

    A version is obsolete once a newer version of the same family is in force.
    """
    def in_force(d: Document) -> bool:
        return d.effective_date <= today and not (d.expiry_date and d.expiry_date < today)

    result = {}
    for doc in docs:
        if doc.expiry_date and doc.expiry_date < today:
            result[doc.id] = ("expired", None)
        elif doc.effective_date > today:
            result[doc.id] = ("upcoming", None)
        else:
            newer = [o for o in docs if o.family == doc.family and o.id != doc.id and in_force(o)
                     and compare_versions(o.version, doc.version) > 0]
            newest = max(newer, key=cmp_to_key(lambda a, b: compare_versions(a.version, b.version)), default=None)
            result[doc.id] = ("obsolete", newest.id) if newest else ("active", None)
    return result


def to_out(db: Session, docs: list[Document]) -> list[DocumentOut]:
    """Attach counts, uploader names and lifecycle in a fixed number of queries."""
    if not docs:
        return []
    ids = [d.id for d in docs]
    chunk_counts = dict(db.execute(
        select(DocumentChunk.document_id, func.count()).where(DocumentChunk.document_id.in_(ids)).group_by(DocumentChunk.document_id)
    ).all())
    flag_counts = dict(db.execute(
        select(InjectionFlag.document_id, func.count()).where(InjectionFlag.document_id.in_(ids)).group_by(InjectionFlag.document_id)
    ).all())
    names = dict(db.execute(select(User.id, User.name).where(User.id.in_({d.uploaded_by_id for d in docs}))).all())
    # Lifecycle depends on sibling versions the caller may not have loaded (e.g. a single-document read).
    families = db.scalars(select(Document).where(Document.family.in_({d.family for d in docs}))).all()
    lifecycle = compute_lifecycle(list(families), date.today())

    out = []
    for doc in docs:
        status, superseded_by = lifecycle[doc.id]
        out.append(DocumentOut.model_validate(doc).model_copy(update={
            "uploaded_by_name": names.get(doc.uploaded_by_id),
            "chunk_count": chunk_counts.get(doc.id, 0),
            "flag_count": flag_counts.get(doc.id, 0),
            "lifecycle_status": status,
            "superseded_by_id": superseded_by,
        }))
    return out


def list_documents(db: Session, user: User) -> list[Document]:
    stmt = select(Document).where(document_filter(user)).order_by(Document.code, Document.version.desc())
    return list(db.scalars(stmt))


def create_document(db: Session, actor: User, meta: DocumentMeta, file_name: str, content: bytes) -> Document:
    """Validate, store and process one uploaded file.

    Processing failures (scanned PDF, bad encoding…) do not reject the upload: the document is kept
    with status `failed` so HR sees why and can retry.
    """
    settings = get_settings()
    ext = file_extension(file_name)
    try:
        check_file(content, ext, settings.max_upload_mb * 1024 * 1024)
    except FileRejected as exc:
        status = 413 if exc.code == "err_file_too_large" else 415 if exc.code == "err_file_type" else 400
        raise AppError(status, exc.code, f"File rejected: {exc.code}", **exc.params) from None

    if db.get(Department, meta.department_code) is None:
        raise AppError(400, "err_department_required", "Unknown department")

    sha256 = hashlib.sha256(content).hexdigest()
    same_file = db.scalar(select(Document).where(Document.sha256 == sha256))
    if same_file:
        raise AppError(409, "err_duplicate_file", "This file is already in the repository",
                       code=same_file.code, version=same_file.version)

    family = family_of(meta.code, meta.title_en)
    code_owner = db.scalar(select(Document).where(Document.code == meta.code, Document.family != family))
    if code_owner:
        raise AppError(409, "err_code_family", "Code already belongs to another document",
                       code=meta.code, title=code_owner.title_en)
    versions = db.scalars(select(Document.version).where(Document.family == family)).all()
    if any(compare_versions(v, meta.version) == 0 for v in versions):
        raise AppError(409, "err_version_exists", "This version already exists", version=meta.version)

    doc_id = new_id("DV")
    doc = Document(
        id=doc_id,
        code=meta.code,
        family=family,
        version=meta.version,
        title=meta.title_en or vietnamese_title(meta.code, meta.title_en),
        title_en=meta.title_en,
        category=meta.category,
        department_code=meta.department_code,
        effective_date=meta.effective_date,
        expiry_date=meta.expiry_date,
        file_name=Path(file_name).name,
        ext=ext,
        mime_type=mimetypes.guess_type(file_name)[0],
        size_bytes=len(content),
        sha256=sha256,
        storage_path=f"{meta.category.lower().replace(' ', '_')}/{doc_id}.{ext}",
        uploaded_by_id=actor.id,
    )
    db.add(doc)
    _apply_processing(db, doc, content)

    target = _file_path(doc)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(content)
    try:
        db.commit()
    except SQLAlchemyError:
        # Without the row nothing points at the file; remove it instead of leaving an orphan.
        target.unlink(missing_ok=True)
        raise
    return doc


def reprocess(db: Session, doc: Document) -> Document:
    """Run extraction again, e.g. after the chunker improved or a transient failure."""
    try:
        content = _file_path(doc).read_bytes()
    except FileNotFoundError:
        raise AppError(410, "err_file_missing", "The stored file is missing; upload it again") from None
    _apply_processing(db, doc, content)
    db.commit()
    return doc


def _apply_processing(db: Session, doc: Document, content: bytes) -> None:
    # Delete old rows with SQL first: the ORM would insert new chunks before deleting old ones and hit
    # the (document_id, chunk_id) unique constraint.
    db.execute(delete(DocumentChunk).where(DocumentChunk.document_id == doc.id))
    db.execute(delete(InjectionFlag).where(InjectionFlag.document_id == doc.id))
    db.flush()
    db.expire(doc, ["chunks", "injection_flags"])

    doc.processed_at = utcnow()
    doc.processing_engine = ENGINE
    try:
        result = process_file(content, doc.ext, doc.code)
    except ExtractionError as exc:
        doc.processing_status = ProcessingStatus.FAILED
        doc.processing_error = exc.code
        doc.page_count = doc.char_count = None
        return

    db.add_all(
        DocumentChunk(document_id=doc.id, position=i, chunk_id=c["chunk_id"], section_id=c["section_id"],
                      heading=c["heading"], page=c["page"], content=c["content"])
        for i, c in enumerate(result.chunks)
    )
    db.add_all(InjectionFlag(document_id=doc.id, **flag) for flag in result.injection_flags)
    doc.processing_status = ProcessingStatus.READY
    doc.processing_error = None
    doc.page_count = result.page_count
    doc.char_count = result.char_count


def get_chunks(db: Session, doc: Document) -> tuple[list[DocumentChunk], list[InjectionFlag]]:
    chunks = db.scalars(select(DocumentChunk).where(DocumentChunk.document_id == doc.id).order_by(DocumentChunk.position))
    flags = db.scalars(select(InjectionFlag).where(InjectionFlag.document_id == doc.id).order_by(InjectionFlag.id))
    return list(chunks), list(flags)


def file_location(doc: Document) -> Path:
    path = _file_path(doc)
    if not path.is_file():
        raise AppError(410, "err_file_missing", "The stored file is missing; upload it again")
    return path


def delete_document(db: Session, doc: Document) -> None:
    in_use = db.scalar(
        select(LearningPath.id)
        .join(PathSource, PathSource.path_id == LearningPath.id)
        .where(PathSource.document_id == doc.id, LearningPath.status.in_(_PATH_STATUSES_LOCKING_SOURCES))
        .limit(1)
    )
    if in_use:
        raise AppError(409, "err_document_in_use", "A learning path under review or published uses this document",
                       path_id=in_use)
    path = _file_path(doc)
    db.delete(doc)
    db.commit()
    path.unlink(missing_ok=True)
