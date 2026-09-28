import hashlib
from pathlib import Path

from docx import Document
from docx.oxml.ns import qn


class DOCXReadError(Exception):
    pass


def _get_doc_id(file_path: Path) -> str:
    sha = hashlib.sha256()
    with open(file_path, "rb") as f:
        while data := f.read(8192):
            sha.update(data)
    return sha.hexdigest()[:12]


def _has_page_break(para) -> bool:
    return any(
        br.get(qn("w:type")) == "page"
        for run in para.runs
        for br in run._element.findall(qn("w:br"))
    )


def read_docx(file_path: Path) -> list[dict]:
    """Read text and tables from a DOCX file page by page with edge case hardening."""
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    doc_id = _get_doc_id(file_path)

    try:
        doc = Document(str(file_path))
    except ValueError as e:
        raise DOCXReadError(f"Cannot read DOCX '{file_path.name}': {e}") from e
    except OSError as e:
        raise DOCXReadError(f"Cannot open file '{file_path.name}': {e}") from e

    if not doc.paragraphs and not doc.tables:
        raise DOCXReadError(f"File '{file_path.name}' has no content.")

    pages = []
    cur_page = 1
    cur_lines = []

    # 1. Extract paragraphs
    for para in doc.paragraphs:
        if _has_page_break(para) and cur_lines:
            pages.append({
                "doc_id": doc_id,
                "page_number": cur_page,
                "raw_text": "\n".join(cur_lines),
                "source_file": file_path.name,
            })
            cur_lines = []
            cur_page += 1

        text = para.text.strip()
        if not text:
            continue

        style = (para.style.name if para.style and para.style.name else "")
        if style.lower().startswith("heading"):
            cur_lines.append(text.upper())
        else:
            cur_lines.append(text)

    # 2. Extract tables (often contains policies, matrices, rules)
    for table in doc.tables:
        for row in table.rows:
            row_cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
            if row_cells:
                cur_lines.append(" | ".join(row_cells))

    if cur_lines:
        pages.append({
            "doc_id": doc_id,
            "page_number": cur_page,
            "raw_text": "\n".join(cur_lines),
            "source_file": file_path.name,
        })

    if not pages:
        raise DOCXReadError(f"File '{file_path.name}' contains no readable text content.")

    return pages

