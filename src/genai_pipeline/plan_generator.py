from src.document_processing.chunker import DocumentChunk
from src.genai_pipeline.gemini_client import generate_content_with_retry
from src.genai_pipeline.response_schemas import OnboardingPlanSchema
from src.prompt_templates.prompt_registry import render_prompt


def _format_chunks_for_prompt(chunks: list[DocumentChunk]) -> str:
    formatted_chunks = []
    for c in chunks:
        formatted_chunks.append(
            f"[Chunk ID: {c.chunk_id} | Page: {c.page_number} | "
            f"Section: {c.heading} | File: {c.source_file} | DocID: {c.doc_id}]\n"
            f"{c.content}\n"
        )
    return "\n".join(formatted_chunks)


def generate_onboarding_plan(
    doc_chunks: list[DocumentChunk],
    role: str,
    prompt_version: str = "v1.0",
) -> OnboardingPlanSchema:
    """Generate an onboarding plan for a specific role from document chunks."""
    if not doc_chunks:
        raise ValueError("doc_chunks cannot be empty.")
    if not role or not role.strip():
        raise ValueError("role cannot be empty.")

    formatted_text = _format_chunks_for_prompt(doc_chunks)

    prompt, version = render_prompt(
        template_name="onboarding_plan",
        version=prompt_version,
        target_role=role.strip(),
        document_chunks=formatted_text,
    )

    raw_json = generate_content_with_retry(
        prompt=prompt,
        response_schema=OnboardingPlanSchema,
    )

    plan = OnboardingPlanSchema.model_validate_json(raw_json)
    plan.prompt_version = version

    return plan
