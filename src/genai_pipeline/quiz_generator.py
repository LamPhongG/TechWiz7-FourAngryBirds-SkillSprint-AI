from pydantic import BaseModel
from src.genai_pipeline.gemini_client import generate_content_with_retry
from src.genai_pipeline.response_schemas import QuizQuestionSchema
from src.prompt_templates.prompt_registry import render_prompt


class QuizListResponse(BaseModel):
    questions: list[QuizQuestionSchema]


def generate_quiz(
    module_content: str,
    module_title: str = "Policy Training",
    target_role: str = "General Employee",
    prompt_version: str = "v1.0",
) -> list[QuizQuestionSchema]:
    """Generate quiz questions based on module content."""
    if not module_content or not module_content.strip():
        raise ValueError("module_content cannot be empty.")

    prompt, _ = render_prompt(
        template_name="quiz_generation",
        version=prompt_version,
        target_role=target_role,
        module_title=module_title,
        module_content=module_content.strip(),
    )

    raw_json = generate_content_with_retry(
        prompt=prompt,
        response_schema=QuizListResponse,
    )

    parsed = QuizListResponse.model_validate_json(raw_json)
    return parsed.questions
