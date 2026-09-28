"""Read the fields of an employee profile (SRS Step 9) from a CV, in pure Python.

Only what the profile needs is taken: name, email, years of experience (for the experience level), a short summary of
previous experience and a list of skills. Phone numbers, addresses, dates of birth, gender and ID numbers are never
read (SRS Step 9: "Sensitive personal information should not be required"), and the file itself is not stored.
The result is a draft the Admin checks before the account is created.
"""
import re
import unicodedata
from datetime import date

from app.ingestion.extract import extract

MAX_EXPERIENCE_CHARS = 600
MAX_SKILLS = 20

_EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_NAME_LABEL = re.compile(r"^\s*(?:họ\s*(?:và)?\s*tên|full\s*name|name|tên)\s*[:\-–]\s*(.+)$", re.IGNORECASE)
_YEARS = re.compile(r"(\d{1,2})\s*\+?\s*(?:năm|years?|yrs?)\b[^\n.]{0,20}?(?:kinh\s*nghiệm|experience)", re.IGNORECASE)
_NOT_A_NAME = re.compile(r"curriculum|vitae|\bcv\b|resume|sơ\s*yếu|lý\s*lịch|profile|hồ\s*sơ", re.IGNORECASE)

# Section headings. A heading is a short line without digits that starts with one of these words and is either written in
# capitals ("KEY SKILLS"), ends with a colon, or has at most two words after the keyword ("Technical skills").
_HEADINGS = {
    "experience": r"kinh\s*nghiệm|work\s*experience|professional\s*experience|experience|employment|work\s*history"
                  r"|quá\s*trình\s*(?:làm\s*việc|công\s*tác)",
    "skills": r"kỹ\s*năng|kĩ\s*năng|(?:technical|soft|hard|core|key|professional)?\s*skills?|competenc(?:y|ies)|năng\s*lực"
              r"|công\s*nghệ|technologies|tech\s*stack",
    "other": r"học\s*vấn|education|chứng\s*chỉ|certificat\w*|dự\s*án|projects?|thông\s*tin|personal|liên\s*hệ|contact"
             r"|sở\s*thích|hobbies|interests|người\s*tham\s*chiếu|references?|mục\s*tiêu|objective|summary|profile"
             r"|tóm\s*tắt|giới\s*thiệu|about|giải\s*thưởng|awards?|thành\s*tích|ngoại\s*ngữ|languages?|hoạt\s*động"
             r"|activities|tham\s*khảo",
}
_HEADING_RE = {k: re.compile(rf"^\s*(?:{v})\b", re.IGNORECASE) for k, v in _HEADINGS.items()}
_BULLET = re.compile(r"^\s*[•·▪◦●\-–*]\s*")
_SEPARATORS = re.compile(r"[,;|•]")


def _heading(line: str) -> str | None:
    text = line.strip().rstrip(":").strip()
    if not text or len(text) > 40 or any(ch.isdigit() for ch in text) or _BULLET.match(line):
        return None
    for kind, rx in _HEADING_RE.items():
        m = rx.match(text)
        if m and (text.isupper() or line.rstrip().endswith(":") or len(text[m.end():].split()) <= 2):
            return kind
    return None


def _split_outside_brackets(line: str) -> list[str]:
    """Split on , ; | • but not inside brackets, so "AWS (S3, EC2)" stays one skill."""
    parts, depth, current = [], 0, ""
    for ch in line:
        depth += ch in "([" and 1 or 0
        depth -= ch in ")]" and 1 or 0
        if depth <= 0 and _SEPARATORS.match(ch):
            parts.append(current)
            current = ""
        else:
            current += ch
    return [*parts, current]


def _is_tag_line(line: str) -> bool:
    """A row of skill tags as a PDF renders them: "TypeScript JavaScript Go", "Node.js Express NestJS"."""
    words = line.split()
    return 1 <= len(words) <= 6 and "&" not in line and all(w[0].isupper() or w[0].isdigit() for w in words)


def _is_list_line(raw: str) -> bool:
    """A line that holds skills: a bullet, a separated list or a row of tags."""
    line = _BULLET.sub("", raw).strip()
    return bool(line) and (bool(_BULLET.match(raw)) or bool(_SEPARATORS.search(line)) or _is_tag_line(line))


def _skills(lines: list[str], name: str | None) -> list[str]:
    skills: list[str] = []
    for i, raw in enumerate(lines):
        # Footer lines ("Candidate Name — CV", the email) end up after the last section of a PDF.
        if "@" in raw or "http" in raw.lower() or (name and name.lower() in raw.lower()):
            continue
        line = _BULLET.sub("", raw).strip()
        if not line or line.endswith(":"):
            continue
        if _BULLET.match(raw) or _SEPARATORS.search(line):
            items = _split_outside_brackets(line)
        elif _is_tag_line(line):
            items = line.split()
        elif i + 1 < len(lines) and _is_list_line(lines[i + 1]):
            continue  # group label above the skills of the group: "Programming languages", "Back-end & Cloud"
        else:
            items = [line]
        for item in items:
            item = item.strip(" -–*•.")
            if 2 <= len(item) <= 60 and item.lower() not in {s.lower() for s in skills}:
                skills.append(item)
    return skills[:MAX_SKILLS]


_MONTH_YEAR = r"(?:\d{1,2}\s*/\s*)?((?:19|20)\d{2})"
_PRESENT = r"hiện\s*tại|nay|present|now|current"
_RANGE = re.compile(rf"{_MONTH_YEAR}\s*[–\-—]\s*(?:{_MONTH_YEAR}|({_PRESENT}))", re.IGNORECASE)


def _years_from_ranges(text: str) -> int | None:
    """Whole years from the first start to the last end of the date ranges in the experience section."""
    starts, ends = [], []
    for m in _RANGE.finditer(text):
        starts.append(int(m.group(1)))
        ends.append(date.today().year if m.group(3) else int(m.group(2)))
    if not starts:
        return None
    return max(0, max(ends) - min(starts))


def _looks_like_name(line: str) -> bool:
    words = line.split()
    if not 2 <= len(words) <= 6 or _NOT_A_NAME.search(line) or "@" in line:
        return False
    return all(w.replace("-", "").isalpha() and (w[0].isupper() or w.isupper()) for w in words)


def _title_case(name: str) -> str:
    return " ".join(w[:1].upper() + w[1:].lower() for w in name.split())


def level_from_years(years: int | None) -> str | None:
    """Experience level of the profile (SRS Step 25): under 2 years Beginner, 2 to 5 Intermediate, above Advanced."""
    if years is None:
        return None
    return "Beginner" if years < 2 else "Intermediate" if years <= 5 else "Advanced"


def parse_text(text: str) -> dict:
    """Profile draft from CV text. Missing fields are `None` / empty and listed in `warnings`."""
    text = unicodedata.normalize("NFC", text or "")
    lines = [re.sub(r"\s+", " ", line).strip() for line in text.splitlines()]
    lines = [line for line in lines if line]

    name = None
    for line in lines[:15]:
        if m := _NAME_LABEL.match(line):
            name = m.group(1).strip()
            break
    if name is None:
        name = next((line for line in lines[:6] if _looks_like_name(line)), None)
    if name and name.isupper():
        name = _title_case(name)

    email = next(iter(_EMAIL.findall(text)), None)
    years = max((int(m.group(1)) for m in _YEARS.finditer(text)), default=None)

    sections: dict[str, list[str]] = {"experience": [], "skills": []}
    current = None
    for line in lines:
        kind = _heading(line)
        if kind:
            current = kind if kind in sections else None
            continue
        if current:
            sections[current].append(line)

    experience = " ".join(sections["experience"])
    if years is None:
        # No "N years experience" sentence: count the years covered by the jobs listed.
        years = _years_from_ranges(experience)
    if len(experience) > MAX_EXPERIENCE_CHARS:
        experience = experience[:MAX_EXPERIENCE_CHARS].rsplit(" ", 1)[0] + "…"
    skills = _skills(sections["skills"], name)

    warnings = [key for key, value in (("cv_warn_no_name", name), ("cv_warn_no_email", email),
                                       ("cv_warn_no_experience", experience), ("cv_warn_no_skills", skills)) if not value]
    return {"name": name, "email": email.lower() if email else None, "years_of_experience": years,
            "experience_level": level_from_years(years), "previous_experience": experience or None,
            "competencies": skills, "warnings": warnings}


def parse_cv(content: bytes, ext: str) -> dict:
    """Profile draft from a CV file (pdf, docx, txt, md).

    Raises:
        ExtractionError: the file cannot be read (corrupt, encrypted, scanned PDF without text).
    """
    extracted = extract(content, ext)
    parts = []
    for block in extracted.blocks:
        if block.heading:
            parts.append(block.heading)
        parts.append(block.text or "")
    return parse_text("\n".join(parts))
