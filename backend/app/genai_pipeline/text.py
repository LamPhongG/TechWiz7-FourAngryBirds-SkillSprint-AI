"""Text helpers shared by the draft generator, citation grounding and path checks.

Ports of frontend `utils/pathGenerator.js` / `utils/chunker.js` helpers; keep them in step so the
browser and the server agree on what "the quote is in the document" means.
"""
import re
import unicodedata

_PARAGRAPH_BREAK = re.compile(r"\n{2,}|\n(?=[-•*]\s)")
_SENTENCE_GAP = re.compile(r"(?<=[.!?])\s+")
_BULLET = re.compile(r"^[-•*]\s+")


def _starts_sentence(piece: str) -> bool:
    """Next piece begins a new sentence: optional opening quote/bracket, then an uppercase letter or digit."""
    head = piece[1:] if piece[:1] in ('"', "“", "(") else piece
    return bool(head) and (head[0] in "0123456789" or head[0].isupper())


def split_sentences(text: str) -> list[str]:
    """Sentences of 25–260 characters, the size that works as a quote, task or quiz statement."""
    sentences = []
    for paragraph in _PARAGRAPH_BREAK.split(text or ""):
        flat = re.sub(r"\s+", " ", paragraph).strip()
        pieces = _SENTENCE_GAP.split(flat) if flat else []
        merged: list[str] = []
        for piece in pieces:
            # Only split before a capital or digit, so "e.g. the manager" stays one sentence.
            if merged and not _starts_sentence(piece):
                merged[-1] = f"{merged[-1]} {piece}"
            else:
                merged.append(piece)
        sentences.extend(_BULLET.sub("", s).strip() for s in merged)
    return [s for s in sentences if 25 <= len(s) <= 260]


def normalize_for_match(text: str | None) -> str:
    """Case, whitespace and typographic quotes/dashes ignored, so a quote survives PDF extraction quirks."""
    text = unicodedata.normalize("NFC", text or "")
    text = re.sub(r"[‘’]", "'", text)
    text = re.sub(r"[“”]", '"', text)
    text = re.sub(r"[–—]", "-", text)
    return re.sub(r"\s+", " ", text).strip().lower()


def stable_hash(text: str) -> int:
    """FNV-1a over UTF-16 code units, identical to the frontend's `stableHash` (answer positions match)."""
    h = 2166136261
    data = text.encode("utf-16-le")
    for i in range(0, len(data), 2):
        code = data[i] | (data[i + 1] << 8)
        h = ((h ^ code) * 16777619) & 0xFFFFFFFF
    return h
