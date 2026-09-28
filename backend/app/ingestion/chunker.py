"""Heading-aware chunking. Port of frontend `utils/chunker.js`: both sides must produce identical
chunk ids, because learning-path citations point at `chunk_id`.

Chunk contract: {doc_id, chunk_id, section_id, heading, page, content}
"""
import csv
import io
import re
from dataclasses import dataclass

from app.ingestion.extract import Block

MAX_CHUNK_CHARS = 1200

# Headings common in policy documents: "1.", "2.3 Title", "Section 4", "Article 5", "Chapter II", markdown "#"
_HEADING_PATTERNS = [
    re.compile(r"^#{1,6}\s+\S"),
    re.compile(r"^(section|chapter|part|article|appendix|điều|chương|phần|phụ lục)\s+[\dIVXLC]+\b", re.IGNORECASE),
]
# Numbered headings start with a capital letter (JS: \p{Lu}), contain no sentence break and are at most 80
# characters after the number. Wrapped PDF body lines such as "5 days until 31 March…" or
# "31 December. This rule has been replaced…" also start with a number but are not headings.
_NUMBERED_HEADING = re.compile(r"^(\d+(\.\d+){0,3})[.)]?\s+(?!.*[.!?]\s)(\S).{0,79}$")
_SENTENCE = re.compile(r"[^.!?。]+[.!?。]*\s*")


def is_heading_line(line: str) -> bool:
    text = line.strip()
    if not text or len(text) > 120:
        return False
    if any(p.search(text) for p in _HEADING_PATTERNS):
        return True
    numbered = _NUMBERED_HEADING.search(text)
    if numbered and numbered.group(3).isupper():
        return True
    # Short all-caps line (PDF title). At least 4 letters so page numbers and bullets don't count.
    letters = "".join(ch for ch in text if ch.isalpha())
    return len(letters) >= 4 and len(text) <= 80 and letters == letters.upper() and not re.search(r"[.,;:]$", text)


def _clean_heading(line: str) -> str:
    return re.sub(r"^#{1,6}\s+", "", line.strip())


@dataclass
class _Part:
    page: int | None
    text: str


@dataclass
class _Section:
    heading: str
    page: int | None
    parts: list[_Part]


def outline(blocks: list[Block]) -> list[str]:
    """Every heading in document order, including parents with no text of their own ("3. Sales Executive" before
    "3.1 Mission"), which never become chunks. Same detection as `chunk_blocks`."""
    headings = []
    for block in blocks:
        if block.heading:
            headings.append(block.heading.strip())
            continue
        headings.extend(_clean_heading(line.rstrip()) for line in re.split(r"\r?\n", block.text or "")
                        if is_heading_line(line.rstrip()))
    return headings


def chunk_blocks(doc_id: str, blocks: list[Block], max_chars: int = MAX_CHUNK_CHARS) -> list[dict]:
    sections: list[_Section] = []

    def start(heading: str, page: int | None) -> _Section:
        section = _Section(heading=heading, page=page, parts=[])
        sections.append(section)
        return section

    current: _Section | None = None
    for block in blocks:
        if block.heading:
            current = start(block.heading.strip(), block.page)
        for raw in re.split(r"\r?\n", block.text or ""):
            line = raw.rstrip()
            if not block.heading and is_heading_line(line):
                current = start(_clean_heading(line), block.page)
                continue
            if not line.strip():
                if current and current.parts:
                    current.parts.append(_Part(page=block.page, text=""))
                continue
            if current is None:
                current = start("", block.page)
            current.parts.append(_Part(page=block.page, text=line.strip()))

    chunks: list[dict] = []
    for index, section in enumerate(sections, start=1):
        for piece in _split_section(section.parts, max_chars):
            chunks.append({
                "doc_id": doc_id,
                "chunk_id": f"{doc_id}-C{len(chunks) + 1:04d}",
                "section_id": f"S{index:03d}",
                "heading": section.heading,
                "page": piece.page if piece.page is not None else section.page,
                "content": piece.text,
            })
    return chunks


def _split_section(parts: list[_Part], max_chars: int) -> list[_Part]:
    """Join lines into paragraphs (split on blank lines), then pack paragraphs up to max_chars."""
    paragraphs: list[_Part] = []
    para: _Part | None = None
    for part in parts:
        if not part.text:
            para = None
            continue
        if para is None:
            para = _Part(page=part.page, text=part.text)
            paragraphs.append(para)
        else:
            para.text += f" {part.text}"

    units = [u for p in paragraphs for u in ([p] if len(p.text) <= max_chars else _split_long(p, max_chars))]
    pieces: list[_Part] = []
    buf: _Part | None = None
    for unit in units:
        if buf and len(buf.text) + len(unit.text) + 2 > max_chars:
            pieces.append(buf)
            buf = None
        if buf is None:
            buf = _Part(page=unit.page, text=unit.text)
        else:
            buf.text += f"\n\n{unit.text}"
    if buf:
        pieces.append(buf)
    return pieces


def _split_long(paragraph: _Part, max_chars: int) -> list[_Part]:
    """Split an oversized paragraph on sentence ends so no chunk runs far past the limit."""
    sentences = _SENTENCE.findall(paragraph.text) or [paragraph.text]
    out: list[_Part] = []
    text = ""
    for sentence in sentences:
        if text and len(text) + len(sentence) > max_chars:
            out.append(_Part(page=paragraph.page, text=text.strip()))
            text = ""
        # A single "sentence" longer than the limit (tables, lists without full stops) is hard-cut.
        if len(sentence) > max_chars:
            out.extend(
                _Part(page=paragraph.page, text=sentence[i:i + max_chars].strip())
                for i in range(0, len(sentence), max_chars)
            )
            continue
        text += sentence
    if text.strip():
        out.append(_Part(page=paragraph.page, text=text.strip()))
    return out


def chunk_csv(doc_id: str, text: str, rows_per_chunk: int = 25) -> list[dict]:
    """Parse CSV documents into traceable chunks.

    If the CSV is pre-structured with section_id / heading / content columns (like DOC-10 SOP),
    each row is preserved as an individual section chunk with its exact section number and heading.
    Otherwise, groups rows up to rows_per_chunk repeating the header row.
    """
    clean_text = text.lstrip("\ufeff")
    lines = [line for line in re.split(r"\r?\n", clean_text) if line.strip()]
    if not lines:
        return []

    # Check for pre-structured chunk CSV
    try:
        reader = csv.DictReader(io.StringIO(clean_text))
        fieldnames = [f.strip().lower() for f in (reader.fieldnames or [])]
        if "content" in fieldnames and ("section_id" in fieldnames or "heading" in fieldnames):
            chunks = []
            for i, row in enumerate(reader, start=1):
                row_map = {k.strip().lower(): v for k, v in row.items() if k}
                content = (row_map.get("content") or "").strip()
                if not content:
                    continue
                raw_section_id = (row_map.get("section_id") or "").strip()
                raw_heading = (row_map.get("heading") or "").strip()

                if raw_section_id and not re.match(r"^\d", raw_heading):
                    heading = f"{raw_section_id}. {raw_heading}".strip()
                else:
                    heading = raw_heading or f"Section {raw_section_id or i}"

                chunk_id = row_map.get("chunk_id") or f"{doc_id}-C{i:04d}"
                if not chunk_id.startswith(doc_id):
                    chunk_id = f"{doc_id}-C{i:04d}"

                chunks.append({
                    "doc_id": doc_id,
                    "chunk_id": chunk_id,
                    "section_id": raw_section_id or f"S{i:03d}",
                    "heading": heading,
                    "page": None,
                    "content": content,
                })
            if chunks:
                return chunks
    except Exception:
        pass

    header, rows = lines[0], lines[1:]
    if not rows:
        return chunk_blocks(doc_id, [Block(page=None, text=header)])
    chunks = []
    for start in range(0, len(rows), rows_per_chunk):
        n = len(chunks) + 1
        chunks.append({
            "doc_id": doc_id,
            "chunk_id": f"{doc_id}-C{n:04d}",
            "section_id": f"S{n:03d}",
            "heading": f"Rows {start + 1}–{min(start + rows_per_chunk, len(rows))}",
            "page": None,
            "content": "\n".join([header, *rows[start:start + rows_per_chunk]]),
        })
    return chunks
