"""Uploaded company documents and the chunks extracted from them."""
from datetime import date, datetime

from sqlalchemy import ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, str_enum, utcnow
from app.models.enums import ProcessingStatus


class Document(Base):
    """One version of a document file.

    Lifecycle labels (active / obsolete / expired / upcoming) are derived from `family`, `version`
    and the dates at read time, so they are not stored.
    """

    __tablename__ = "documents"
    __table_args__ = (UniqueConstraint("code", "version"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    code: Mapped[str] = mapped_column(String(32), index=True)
    # Groups versions of the same document, e.g. DOC-01 and DOC-02 are both "employee-handbook".
    family: Mapped[str] = mapped_column(String(96), index=True)
    version: Mapped[str] = mapped_column(String(16))
    title: Mapped[str] = mapped_column(String(255))
    title_en: Mapped[str] = mapped_column(String(255))
    category: Mapped[str] = mapped_column(String(32))
    department_code: Mapped[str] = mapped_column(ForeignKey("departments.code"))
    effective_date: Mapped[date]
    expiry_date: Mapped[date | None]

    file_name: Mapped[str] = mapped_column(String(255))
    ext: Mapped[str] = mapped_column(String(8))
    mime_type: Mapped[str | None] = mapped_column(String(128))
    size_bytes: Mapped[int]
    # Same file uploaded twice is rejected, whatever name it has.
    sha256: Mapped[str] = mapped_column(String(64), unique=True)
    # Path relative to settings.upload_dir, so the upload folder can move between machines.
    storage_path: Mapped[str] = mapped_column(String(512))

    processing_status: Mapped[ProcessingStatus] = mapped_column(
        str_enum(ProcessingStatus, "processing_status"), default=ProcessingStatus.PENDING
    )
    processing_engine: Mapped[str | None] = mapped_column(String(32))
    processing_error: Mapped[str | None] = mapped_column(String(64))
    page_count: Mapped[int | None]
    char_count: Mapped[int | None]
    processed_at: Mapped[datetime | None]

    uploaded_by_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    uploaded_at: Mapped[datetime] = mapped_column(default=utcnow)

    chunks: Mapped[list["DocumentChunk"]] = relationship(
        back_populates="document", cascade="all, delete-orphan", passive_deletes=True, order_by="DocumentChunk.position"
    )
    injection_flags: Mapped[list["InjectionFlag"]] = relationship(cascade="all, delete-orphan", passive_deletes=True)


class DocumentChunk(Base):
    """Chunk contract shared with ingestion: {doc_id, chunk_id, section_id, heading, page, content}."""

    __tablename__ = "document_chunks"
    # chunk_id (e.g. DOC-10-C0001) repeats across versions of the same code, so it is unique per document row.
    __table_args__ = (UniqueConstraint("document_id", "chunk_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"))
    chunk_id: Mapped[str] = mapped_column(String(48))
    section_id: Mapped[str | None] = mapped_column(String(48))
    heading: Mapped[str | None] = mapped_column(String(255))
    page: Mapped[int | None]
    position: Mapped[int]
    content: Mapped[str] = mapped_column(Text)

    document: Mapped[Document] = relationship(back_populates="chunks")


class InjectionFlag(Base):
    """Prompt-injection match found in a chunk (same shape as frontend `scanChunks`)."""

    __tablename__ = "injection_flags"
    __table_args__ = (Index("ix_injection_flags_document_chunk", "document_id", "chunk_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"))
    chunk_id: Mapped[str] = mapped_column(String(48))
    page: Mapped[int | None]
    rule_id: Mapped[str] = mapped_column(String(64))
    severity: Mapped[str] = mapped_column(String(16))
    match: Mapped[str] = mapped_column(Text)
    excerpt: Mapped[str] = mapped_column(Text)
