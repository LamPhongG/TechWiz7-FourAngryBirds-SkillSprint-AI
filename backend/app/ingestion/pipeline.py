"""Single entry point: file bytes → chunks + injection flags."""
from dataclasses import dataclass

from app.core.injection_filter import scan_chunks
from app.ingestion.chunker import chunk_blocks, chunk_csv
from app.ingestion.extract import ExtractionError, extract

ENGINE = "backend"


@dataclass
class ProcessingResult:
    chunks: list[dict]
    injection_flags: list[dict]
    page_count: int | None
    char_count: int


def process_file(content: bytes, ext: str, doc_code: str) -> ProcessingResult:
    """Extract, chunk and screen one document.

    Args:
        content: raw file bytes (already passed `validation.check_file`).
        ext: lowercase extension without the dot.
        doc_code: document code such as DOC-10; prefixes every chunk_id.

    Raises:
        ExtractionError: CORRUPT_FILE, ENCRYPTED, BAD_ENCODING, NO_TEXT_LAYER (scanned PDF) or NO_TEXT.
    """
    extracted = extract(content, ext)
    chunks = chunk_csv(doc_code, extracted.raw or "") if ext == "csv" else chunk_blocks(doc_code, extracted.blocks)
    if not chunks:
        # A PDF with pages but no text layer is a scan: tell HR it needs OCR rather than "empty".
        raise ExtractionError("NO_TEXT_LAYER" if ext == "pdf" else "NO_TEXT")
    return ProcessingResult(
        chunks=chunks,
        injection_flags=scan_chunks(chunks),
        page_count=extracted.page_count,
        char_count=sum(len(c["content"]) for c in chunks),
    )
