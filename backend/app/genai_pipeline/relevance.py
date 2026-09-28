"""Send the model only what the target role needs from each document (SRS: role-relevant chunks).

A shared document often holds sections for several roles: DOC-14 describes four jobs, DOC-12 has a section only for
the Branch Manager, DOC-20 lists exceptions per department. A section is set aside for this role when its heading, or
a parent heading, belongs to someone else:
- it names another job position ("3. Sales Executive") and not this one;
- it is tagged for another role ("[ROLE-SPECIFIC: Branch Manager]");
- it is a department exception ("Finance – Month-End Leave Blackout [EXCEPTION]") for another department.

A section that the role's own Role Requirement Matrix rows cite is always kept. Everything else — general rules,
shared sections, sections that name nobody — is kept, so the filter only removes what clearly belongs to others.
"""
import re
from dataclasses import replace

from app.genai_pipeline.types import RoleScope, SourceDoc
from app.rule_pipeline.requirements import section_number

_ROLE_TAG = re.compile(r"\[ROLE-SPECIFIC:\s*([^\]]+)\]", re.IGNORECASE)
_EXCEPTION = re.compile(r"\[EXCEPTION\]", re.IGNORECASE)
_DASH = re.compile(r"\s+[–—-]\s+")


def _mentions(text: str, name: str) -> bool:
    name = re.sub(r"\s*/\s*", " / ", name.strip())
    text = re.sub(r"\s*/\s*", " / ", text)
    return bool(re.search(rf"(?<!\w){re.escape(name)}(?!\w)", text, re.IGNORECASE))


def belongs_to_others(heading: str, scope: RoleScope) -> bool:
    tag = _ROLE_TAG.search(heading)
    if tag:
        return not _mentions(tag.group(1), scope.role)
    if _mentions(heading, scope.role):
        return False
    if any(_mentions(heading, other) for other in scope.other_roles):
        return True
    if _EXCEPTION.search(heading):
        # "Engineering & Support – On-Call Rotation [EXCEPTION]": the part before the dash says whose exception it is.
        owner = _DASH.split(re.sub(r"^\d+(\.\d+)*\.?\s*", "", heading), maxsplit=1)[0]
        if _mentions(owner, scope.department):
            return False
        return any(_mentions(owner, d) for d in scope.other_departments)
    return False


def _ancestors(number: str) -> list[str]:
    parts = number.split(".")
    return [".".join(parts[:i]) for i in range(len(parts), 0, -1)]


def filter_for_role(doc: SourceDoc, scope: RoleScope, cited_sections: list[str | None]) -> tuple[SourceDoc, list[dict]]:
    """(document with only the role's chunks, sections set aside as [{doc, section, heading, chunks}])."""
    if any(s is None for s in cited_sections):
        return doc, []  # a requirement on the whole document: keep everything
    by_number = {n: h for h in doc.outline if (n := section_number(h))}
    kept, dropped = [], {}
    for chunk in doc.chunks:
        number = section_number(chunk["heading"])
        lineage = _ancestors(number) if number else []
        cited = any(c == n or c.startswith(n + ".") or n.startswith(c + ".") for c in cited_sections for n in lineage[:1])
        # Report the highest heading that belongs to someone else: "3. Sales Executive", not each of its subsections.
        owner = next((n for n in reversed(lineage) if belongs_to_others(by_number.get(n) or chunk["heading"], scope)), None)
        if owner is None or cited:
            kept.append(chunk)
            continue
        entry = dropped.setdefault(owner, {"doc": doc.code, "section": owner, "heading": by_number.get(owner, chunk["heading"]),
                                           "chunks": 0})
        entry["chunks"] += 1
    return replace(doc, chunks=kept), list(dropped.values())
