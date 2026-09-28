"""Matching learning-path items to Role Requirement Matrix rows (pure Python, no AI SDK).

Requirements arrive as plain dicts (`services.role_matrix.as_generation_dict`). An item is matched to requirements by
the document code and section number of its own citation, computed here, never claimed by a model. Pipeline 1 uses
these functions to tag what it wrote; Pipeline 2 uses them to evaluate coverage on the final content.
"""
import re

_SECTION_NUMBER = re.compile(r"^§?\s*(\d+(?:\.\d+)*)")


def section_number(text: str | None) -> str | None:
    """'4.2 Tier 2 – Formal Escalation…' → '4.2'; '§6' → '6'; no leading number → None."""
    m = _SECTION_NUMBER.match((text or "").strip())
    return m.group(1) if m else None


def for_document(requirements: list[dict], doc_code: str) -> list[dict]:
    """Requirements citing one document, mandatory first."""
    return sorted((r for r in requirements if r["source_doc_code"] == doc_code),
                  key=lambda r: (not r["mandatory"], r["id"]))


def matching(requirements: list[dict], doc_code: str | None, section: str | None) -> list[dict]:
    """Requirements an item from `doc_code` §`section` teaches.

    A requirement on §4 is taught by items from 4, 4.1, 4.2…; one without a section covers the whole document.
    """
    out = []
    for req in requirements:
        if req["source_doc_code"] != doc_code:
            continue
        wanted = req["source_section"]
        if section is None or wanted is None or section == wanted or section.startswith(wanted + "."):
            out.append(req)
    return out


def module_items(module: dict):
    """(kind, item) for every lesson, task and quiz question of a module."""
    for kind, key in (("lesson", "lessons"), ("task", "tasks"), ("quiz", "quiz")):
        for item in module.get(key, []):
            yield kind, item


def tag_modules(modules: list[dict], requirements: list[dict]) -> dict:
    """Write `requirement_ids` on every item and module, and return the coverage of the role's requirements.

    A requirement is taught when a lesson comes from its section, and assessed when a task or quiz question does.
    """
    taught: set[str] = set()
    assessed: set[str] = set()
    for module in modules:
        module_ids: list[str] = []
        for kind, item in module_items(module):
            ref = item.get("source_reference") or {}
            ids = [r["id"] for r in matching(requirements, ref.get("doc") or module.get("doc_code"),
                                             section_number(ref.get("section")))]
            if not ids:
                item.pop("requirement_ids", None)
                item.pop("mandatory", None)
                continue
            item["requirement_ids"] = ids
            item["mandatory"] = any(r["mandatory"] for r in requirements if r["id"] in ids)
            module_ids.extend(ids)
            (taught if kind == "lesson" else assessed).update(ids)
        if module_ids:
            module["requirement_ids"] = sorted(set(module_ids))
        # Mandatory module: the role's matrix makes its document compulsory (SRS Step 10).
        module["mandatory"] = any(r["mandatory"] for r in for_document(requirements, module.get("doc_code")))
    mandatory = sorted(r["id"] for r in requirements if r["mandatory"])
    return {
        "total": len(requirements),
        "mandatory": len(mandatory),
        "taught": sorted(taught),
        "assessed": sorted(assessed),
        "mandatory_not_taught": [i for i in mandatory if i not in taught],
        "mandatory_not_assessed": [i for i in mandatory if i in taught and i not in assessed],
    }
