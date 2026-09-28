"""Coverage of a role's Role Requirement Matrix by a learning path (SRS Step 28-29), pure Python.

Evaluated on the final path content: every lesson, task and quiz question is matched to requirements through the
document code and section number of its own citation. Requirement ids already stored on items (written by Pipeline 1
or edited by hand) are ignored, so the score cannot be influenced by what the generator claims.
"""
from collections import defaultdict

from app.rule_pipeline.requirements import module_items, section_number


def _matches(requirement: dict, doc_code: str | None, section: str | None) -> bool:
    """Stricter than Pipeline 1's tagging: an item whose citation has no section number only covers requirements that
    apply to the whole document, otherwise one vague citation would cover every section of it."""
    if not doc_code or requirement["source_doc_code"] != doc_code:
        return False
    wanted = requirement["source_section"]
    if wanted is None:
        return True
    return section is not None and (section == wanted or section.startswith(wanted + "."))


def evaluate_requirements(stages: list[dict], requirements: list[dict]) -> dict:
    """SRS Step 28 figures for one path against one role's requirements.

    Returns `score` (covered mandatory / total mandatory, `None` when the role has no mandatory requirement), the
    requirement ids `covered`, `missing`, `not_assessed` and `duplicate` (taught by more than one module), and
    `unmatched_items`: items whose citation matches no requirement of the role.
    """
    taught_by: dict[str, set[str]] = defaultdict(set)
    assessed: set[str] = set()
    unmatched = 0
    items = 0
    for stage in stages:
        for module in stage.get("modules", []):
            if module.get("kind") == "assessment":
                continue  # the final assessment repeats earlier questions; counting it would hide missing assessment
            for kind, item in module_items(module):
                items += 1
                ref = item.get("source_reference") or {}
                doc_code, section = ref.get("doc") or module.get("doc_code"), section_number(ref.get("section"))
                hits = [r["id"] for r in requirements if _matches(r, doc_code, section)]
                if not hits:
                    unmatched += 1
                for rid in hits:
                    if kind == "lesson":
                        taught_by[rid].add(module.get("id"))
                    else:
                        assessed.add(rid)

    mandatory = sorted(r["id"] for r in requirements if r["mandatory"])
    covered = [rid for rid in mandatory if rid in taught_by]
    return {
        "score": len(covered) / len(mandatory) if mandatory else None,
        "required": len(mandatory),
        "covered": covered,
        "missing": [rid for rid in mandatory if rid not in taught_by],
        "not_assessed": [rid for rid in covered if rid not in assessed],
        "duplicate": sorted(rid for rid, modules in taught_by.items() if len(modules) > 1),
        "unmatched_items": unmatched,
        "items": items,
    }
