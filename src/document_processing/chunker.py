import re
import uuid
from typing import NamedTuple

HEADING_PATTERNS = [
    re.compile(r"^(CHAPTER|SECTION|PART)\s+[\dIVXA-Z]+[\.:\s]", re.IGNORECASE),
    re.compile(r"^\d+(\.\d+)*\s+[A-Z]"),
    re.compile(r"^[A-Z][A-Z\s]{4,}$"),
    re.compile(r"^[A-Z][^.!?]{5,50}:$"),
]

MIN_CHUNK = 80
MAX_CHUNK = 2000


class DocumentChunk(NamedTuple):
    doc_id: str
    chunk_id: str
    section_id: int
    heading: str
    page_number: int
    content: str
    source_file: str


def _is_heading(line: str) -> bool:
    return any(p.match(line.strip()) for p in HEADING_PATTERNS)


def _make_chunk(doc_id, section_id, heading, page_number, lines, source_file):
    text = " ".join(lines).strip()
    if len(text) < MIN_CHUNK:
        return None
    if len(text) > MAX_CHUNK:
        text = text[:MAX_CHUNK]
    return DocumentChunk(
        doc_id=doc_id,
        chunk_id=str(uuid.uuid4()),
        section_id=section_id,
        heading=heading,
        page_number=page_number,
        content=text,
        source_file=source_file,
    )


def split_into_chunks(raw_pages: list[dict]) -> list[DocumentChunk]:
    """Split page text into chunks based on headings."""
    if not raw_pages:
        raise ValueError("raw_pages cannot be empty.")

    required = {"doc_id", "page_number", "raw_text", "source_file"}
    for i, page in enumerate(raw_pages):
        missing = required - page.keys()
        if missing:
            raise ValueError(f"Page {i} is missing required keys: {missing}")

    doc_id = raw_pages[0]["doc_id"]
    source_file = raw_pages[0]["source_file"]

    result = []
    cur_heading = "Introduction"
    cur_page = raw_pages[0]["page_number"]
    cur_lines = []
    section_id = 0

    for page in raw_pages:
        for line in page["raw_text"].splitlines():
            line = line.strip()
            if not line:
                continue

            if _is_heading(line):
                chunk = _make_chunk(doc_id, section_id, cur_heading, cur_page, cur_lines, source_file)
                if chunk:
                    result.append(chunk)
                section_id += 1
                cur_heading = line
                cur_page = page["page_number"]
                cur_lines = []
            else:
                cur_lines.append(line)

    last = _make_chunk(doc_id, section_id, cur_heading, cur_page, cur_lines, source_file)
    if last:
        result.append(last)

    return result
