"""Document upload metadata and responses."""
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.ingestion.validation import CODE_PATTERN, VERSION_PATTERN, normalize_version
from app.models import ProcessingStatus
from app.services.document_catalog import CATEGORIES


class DocumentMeta(BaseModel):
    """Form fields sent with the file in `POST /documents` (multipart)."""

    code: str = Field(max_length=32)
    title_en: str = Field(min_length=1, max_length=255)
    category: str
    department_code: str = Field(max_length=64)
    version: str = Field(max_length=16)
    effective_date: date
    expiry_date: date | None = None

    @field_validator("code")
    @classmethod
    def check_code(cls, value: str) -> str:
        value = value.strip().upper()
        if not CODE_PATTERN.match(value):
            raise ValueError("Code must look like DOC-01")
        return value

    @field_validator("version")
    @classmethod
    def check_version(cls, value: str) -> str:
        value = normalize_version(value)
        if not VERSION_PATTERN.match(value):
            raise ValueError("Version must look like 1.0 or 2.1.3")
        return value

    @field_validator("title_en")
    @classmethod
    def strip_title(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Title is required")
        return value

    @field_validator("category")
    @classmethod
    def check_category(cls, value: str) -> str:
        if value not in CATEGORIES:
            raise ValueError(f"Category must be one of: {', '.join(CATEGORIES)}")
        return value

    @model_validator(mode="after")
    def check_dates(self) -> "DocumentMeta":
        if self.expiry_date and self.expiry_date <= self.effective_date:
            raise ValueError("Expiry date must be after the effective date")
        return self


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    code: str
    family: str
    version: str
    title: str
    title_en: str
    category: str
    department_code: str
    effective_date: date
    expiry_date: date | None
    file_name: str
    ext: str
    mime_type: str | None
    size_bytes: int
    sha256: str
    uploaded_by_id: str
    uploaded_by_name: str | None = None
    uploaded_at: datetime
    processing_status: ProcessingStatus
    processing_engine: str | None
    processing_error: str | None
    page_count: int | None
    char_count: int | None
    processed_at: datetime | None
    chunk_count: int = 0
    flag_count: int = 0
    # Derived at read time: active / obsolete / expired / upcoming
    lifecycle_status: str = "active"
    superseded_by_id: str | None = None


class ChunkOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    chunk_id: str
    section_id: str | None
    heading: str | None
    page: int | None
    content: str


class InjectionFlagOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    chunk_id: str
    page: int | None
    rule_id: str
    severity: str
    match: str
    excerpt: str


class DocumentChunksOut(BaseModel):
    """Same shape as the browser processing result, so the chunk viewer works unchanged."""

    document_id: str
    engine: str | None
    chunks: list[ChunkOut]
    injection_flags: list[InjectionFlagOut]
    page_count: int | None
    char_count: int | None
    processed_at: datetime | None
