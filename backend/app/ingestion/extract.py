"""Text extraction for PDF, DOCX, TXT, MD and CSV.

Output mirrors frontend `services/textExtraction.js` so browser and backend processing produce the
same chunks: PDF gives one block per page, DOCX one block per heading (no page numbers).
"""
import io
import re
import zipfile
from dataclasses import dataclass

import docx
import pymupdf
from docx.opc.exceptions import PackageNotFoundError
from docx.table import Table


@dataclass
class Block:
    page: int | None
    text: str
    heading: str | None = None


@dataclass
class Extracted:
    blocks: list[Block]
    page_count: int | None
    raw: str | None = None


class ExtractionError(Exception):
    """Content cannot be read. `code` is stored in `documents.processing_error`."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def extract(content: bytes, ext: str) -> Extracted:
    if ext == "pdf":
        return _extract_pdf(content)
    if ext == "docx":
        return _extract_docx(content)
    if ext in ("txt", "md", "csv"):
        text = _decode_text(content)
        return Extracted(blocks=[Block(page=None, text=text)], page_count=None, raw=text)
    raise NotImplementedError(f"Unsupported format: .{ext}")


def _extract_pdf(content: bytes) -> Extracted:
    try:
        pdf = pymupdf.open(stream=content, filetype="pdf")
    except pymupdf.FileDataError:
        raise ExtractionError("CORRUPT_FILE") from None
    with pdf:
        if pdf.needs_pass:
            raise ExtractionError("ENCRYPTED")
        blocks = [Block(page=number, text=page.get_text("text")) for number, page in enumerate(pdf, start=1)]
        return Extracted(blocks=blocks, page_count=pdf.page_count)


def _extract_docx(content: bytes) -> Extracted:
    try:
        document = docx.Document(io.BytesIO(content))
    except (PackageNotFoundError, zipfile.BadZipFile, KeyError, ValueError):
        raise ExtractionError("CORRUPT_FILE") from None

    blocks: list[Block] = []
    heading, parts = "", []

    def flush() -> None:
        if parts or heading:
            blocks.append(Block(page=None, heading=heading, text="".join(parts)))

    for item in document.iter_inner_content():
        if isinstance(item, Table):
            rows = [" | ".join(cell.text.strip() for cell in row.cells) for row in item.rows]
            parts.append("\n".join(rows) + "\n\n")
            continue
        text = re.sub(r"\s+", " ", item.text).strip()
        if not text:
            continue
        style = (item.style.name if item.style is not None else "").lower()
        if style.startswith("heading") or style == "title":
            flush()
            heading, parts = text, []
        elif style.startswith("list"):
            parts.append(f"- {text}\n\n")
        else:
            parts.append(f"{text}\n\n")
    flush()
    return Extracted(blocks=blocks, page_count=None)


def _decode_text(content: bytes) -> str:
    # Windows tools (Notepad, Excel "Unicode text") still write UTF-16 with a BOM.
    encoding = "utf-16" if content.startswith((b"\xff\xfe", b"\xfe\xff")) else "utf-8-sig"
    try:
        return content.decode(encoding)
    except UnicodeDecodeError:
        raise ExtractionError("BAD_ENCODING") from None
