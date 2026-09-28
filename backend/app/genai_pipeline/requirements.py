"""Role Requirement Matrix inside Pipeline 1: how the role's requirements are briefed to the model.

Matching items to requirements is pure Python and lives in `app.rule_pipeline.requirements`, shared with Pipeline 2;
it is re-exported here because the generator uses it to tag what it wrote.
"""
from app.rule_pipeline.requirements import for_document, matching, section_number, tag_modules

__all__ = ["for_document", "format_for_prompt", "matching", "section_number", "tag_modules"]


def format_for_prompt(requirements: list[dict]) -> str:
    if not requirements:
        return "(none listed for this document; teach its most important obligations for the role)"
    lines = []
    for r in requirements:
        where = f"\u00a7{r['source_section']}" if r["source_section"] else "whole document"
        kind = "Mandatory" if r["mandatory"] else "Optional"
        line = f"- {r['id']} [{kind}, {r['priority']} priority, {where}]: {r['text']}"
        if r.get("assessment"):
            line += f" \u2014 assessed by: {r['assessment']}"
        lines.append(line)
    return "\n".join(lines)
