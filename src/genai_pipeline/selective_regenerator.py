"""Selective Regeneration Engine.

Enables updating only affected modules or quizzes when policies change,
preserving unaffected content and keeping the onboarding plan stable.
"""

import copy
from typing import Any
from pydantic import BaseModel
from src.document_processing.chunker import DocumentChunk
from src.genai_pipeline.gemini_client import generate_content_with_retry
from src.genai_pipeline.response_schemas import ModuleSchema, OnboardingPlanSchema


class RegeneratedModulesResponse(BaseModel):
    modules: list[ModuleSchema]


def _format_chunks_for_prompt(chunks: list[DocumentChunk]) -> str:
    formatted = []
    for c in chunks:
        formatted.append(
            f"[Chunk ID: {c.chunk_id} | Page: {c.page_number} | "
            f"Section: {c.heading} | File: {c.source_file} | DocID: {c.doc_id}]\n"
            f"{c.content}\n"
        )
    return "\n".join(formatted)


def regenerate_affected_modules(
    existing_plan: OnboardingPlanSchema,
    affected_module_ids: list[str],
    updated_chunks: list[DocumentChunk],
    target_role: str | None = None,
) -> tuple[OnboardingPlanSchema, dict[str, Any]]:
    """Selectively regenerate only affected modules, preserving unaffected modules.
    
    Returns:
        (updated_plan, regeneration_report)
    """
    if not affected_module_ids:
        return existing_plan, {"regenerated_count": 0, "message": "No modules specified."}

    role = target_role or existing_plan.target_role
    affected_set = set(affected_module_ids)

    # Find the target modules to regenerate
    target_modules = [m for m in existing_plan.modules if m.module_id in affected_set]
    if not target_modules:
        return existing_plan, {"regenerated_count": 0, "error": "None of the specified module_ids were found in plan."}

    target_titles = [m.title for m in target_modules]
    formatted_chunks = _format_chunks_for_prompt(updated_chunks)

    selective_prompt = (
        f"You are an expert HR Onboarding Specialist.\n"
        f"A corporate policy has been updated. Regenerate ONLY the following affected onboarding modules "
        f"tailored for the role: '{role}'.\n\n"
        f"### AFFECTED MODULES TO REGENERATE:\n"
        + "\n".join(f"- Module ID: {m.module_id} | Title: {m.title}" for m in target_modules)
        + f"\n\n### UPDATED POLICY DOCUMENT CHUNKS:\n"
        f"{formatted_chunks}\n\n"
        f"### INSTRUCTIONS:\n"
        f"1. Generate updated content strictly for the {len(target_modules)} requested modules.\n"
        f"2. Keep the original module_id for each regenerated module.\n"
        f"3. Include actionable tasks and 1 quiz question with valid source citations.\n"
        f"4. For any practical assessment, include a rubric with criterion, weight, expected_performance, pass_condition.\n"
        f"5. Output valid JSON matching RegeneratedModulesResponse."
    )

    raw_json = generate_content_with_retry(
        prompt=selective_prompt,
        response_schema=RegeneratedModulesResponse,
    )

    parsed = RegeneratedModulesResponse.model_validate_json(raw_json)
    regenerated_map = {m.module_id: m for m in parsed.modules}

    # Clone the existing plan
    updated_plan_dict = existing_plan.model_dump()
    new_modules_list = []

    for old_m in existing_plan.modules:
        if old_m.module_id in regenerated_map:
            # Replace with regenerated module, retaining order index
            repl = regenerated_map[old_m.module_id]
            repl.order_index = old_m.order_index
            new_modules_list.append(repl)
        else:
            # Preserve unaffected module intact
            new_modules_list.append(old_m)

    new_plan = OnboardingPlanSchema(
        plan_id=existing_plan.plan_id,
        target_role=existing_plan.target_role,
        title=existing_plan.title,
        summary=existing_plan.summary,
        prompt_version=existing_plan.prompt_version,
        modules=new_modules_list,
        source_citation=existing_plan.source_citation,
    )

    report = {
        "status": "success",
        "regenerated_module_ids": list(regenerated_map.keys()),
        "regenerated_count": len(regenerated_map),
        "preserved_count": len(existing_plan.modules) - len(regenerated_map),
        "policy_chunks_used": len(updated_chunks),
    }

    return new_plan, report
