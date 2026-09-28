import hashlib
from pathlib import Path
import unicodedata

try:
    import pymupdf as fitz
except ImportError:
    import fitz



class PDFReadError(Exception):
    pass


def _get_doc_id(file_path: Path) -> str:
    sha = hashlib.sha256()
    with open(file_path, "rb") as f:
        while data := f.read(8192):
            sha.update(data)
    return sha.hexdigest()[:12]


def read_pdf(file_path: Path) -> list[dict]:
    """Read text from each page of a PDF file with edge case hardening."""
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    doc_id = _get_doc_id(file_path)
    pages = []

    try:
        pdf = fitz.open(str(file_path))
    except fitz.FileDataError as e:
        raise PDFReadError(f"Cannot read PDF '{file_path.name}': {e}") from e

    try:
        if pdf.is_encrypted:
            raise PDFReadError(f"PDF '{file_path.name}' is encrypted or password-protected.")

        if pdf.page_count == 0:
            raise PDFReadError(f"File '{file_path.name}' has no pages.")

        for i in range(pdf.page_count):
            raw = str(pdf[i].get_text("text")).strip()
            if not raw:
                continue
            # Normalize Unicode characters (e.g. Vietnamese NFD to NFC)
            text = unicodedata.normalize("NFC", raw)
            pages.append({
                "doc_id": doc_id,
                "page_number": i + 1,
                "raw_text": text,
                "source_file": file_path.name,
            })

        if pdf.page_count > 0 and len(pages) == 0:
            raise PDFReadError(
                f"PDF '{file_path.name}' contains no selectable text (scanned image-only document)."
            )
    finally:
        pdf.close()

    return pages

