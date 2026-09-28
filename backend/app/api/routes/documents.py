from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse
from pydantic import ValidationError

from app.api.deps import CurrentUser, DbSession, require_roles
from app.core.config import get_settings
from app.models import User, UserRole
from app.schemas.documents import DocumentChunksOut, DocumentMeta, DocumentOut
from app.services import documents as service

router = APIRouter(prefix="/documents", tags=["documents"])

HrUser = Annotated[User, Depends(require_roles(UserRole.HR))]
# Endpoints accessible to staff and admin users.
StaffUser = Annotated[User, Depends(require_roles(UserRole.HR, UserRole.REVIEWER, UserRole.ADMIN))]


def document_meta(
    code: Annotated[str, Form()],
    title_en: Annotated[str, Form()],
    category: Annotated[str, Form()],
    department_code: Annotated[str, Form()],
    version: Annotated[str, Form()],
    effective_date: Annotated[date, Form()],
    expiry_date: Annotated[str | None, Form()] = None,
) -> DocumentMeta:
    # FastAPI cannot bind a Pydantic model from form fields when a File is in the same request,
    # so the fields are declared one by one and validated here.
    try:
        return DocumentMeta(code=code, title_en=title_en, category=category, department_code=department_code,
                            version=version, effective_date=effective_date,
                            # An empty date input is submitted as "", meaning "no expiry".
                            expiry_date=expiry_date or None)
    except ValidationError as exc:
        raise RequestValidationError(exc.errors(include_url=False)) from None


@router.get("", response_model=list[DocumentOut])
def list_documents(db: DbSession, user: CurrentUser):
    """HR / Reviewer: whole repository. Employee: company-wide, own department, sources of assigned paths."""
    return service.to_out(db, service.list_documents(db, user))


@router.post("", response_model=DocumentOut, status_code=status.HTTP_201_CREATED)
async def upload_document(
    db: DbSession,
    user: HrUser,
    meta: Annotated[DocumentMeta, Depends(document_meta)],
    file: Annotated[UploadFile, File()],
):
    """Upload one file with its metadata. It is extracted, chunked and screened before the response.

    Check `processing_status`: `ready`, or `failed` with `processing_error`
    (NO_TEXT_LAYER = scanned PDF, CORRUPT_FILE, ENCRYPTED, BAD_ENCODING, NO_TEXT).
    """
    max_bytes = get_settings().max_upload_mb * 1024 * 1024
    # Read one byte past the limit so an oversized file is detected without loading all of it.
    content = await file.read(max_bytes + 1)
    doc = service.create_document(db, user, meta, file.filename or "upload", content)
    return service.to_out(db, [doc])[0]


@router.get("/{doc_id}", response_model=DocumentOut)
def get_document(doc_id: str, db: DbSession, user: CurrentUser):
    return service.to_out(db, [service.get_visible(db, user, doc_id)])[0]


@router.get("/{doc_id}/chunks", response_model=DocumentChunksOut)
def get_document_chunks(doc_id: str, db: DbSession, user: StaffUser):
    doc = service.get_visible(db, user, doc_id)
    chunks, flags = service.get_chunks(db, doc)
    return DocumentChunksOut(
        document_id=doc.id, engine=doc.processing_engine, chunks=chunks, injection_flags=flags,
        page_count=doc.page_count, char_count=doc.char_count, processed_at=doc.processed_at,
    )


@router.get("/{doc_id}/file")
def download_document(doc_id: str, db: DbSession, user: CurrentUser):
    """Original file. Served inline so a PDF opens in the browser and `#page=N` citations work."""
    doc = service.get_visible(db, user, doc_id)
    return FileResponse(
        service.file_location(doc),
        media_type=doc.mime_type or "application/octet-stream",
        filename=doc.file_name,
        content_disposition_type="inline",
    )


@router.post("/{doc_id}/process", response_model=DocumentOut)
def reprocess_document(doc_id: str, db: DbSession, user: HrUser):
    """Retry extraction (the *Retry* button for failed documents)."""
    doc = service.reprocess(db, service.get_visible(db, user, doc_id))
    return service.to_out(db, [doc])[0]


@router.delete("/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(doc_id: str, db: DbSession, user: HrUser):
    service.delete_document(db, service.get_visible(db, user, doc_id))
