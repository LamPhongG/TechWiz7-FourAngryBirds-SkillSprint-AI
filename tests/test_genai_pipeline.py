# Unit tests for GenAI pipeline, prompt registry, and response schemas

import json
from unittest.mock import patch
import pytest
from pydantic import ValidationError

from src.document_processing.chunker import DocumentChunk
from src.genai_pipeline.gemini_client import GeminiAPIError, configure_client
from src.genai_pipeline.plan_generator import generate_onboarding_plan
from src.genai_pipeline.quiz_generator import generate_quiz
from src.genai_pipeline.response_schemas import (
    OnboardingPlanSchema,
    SourceCitation,
    TaskSchema,
)
from src.prompt_templates.prompt_registry import (
    TemplateNotFoundError,
    get_prompt_template,
    render_prompt,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sample_citation():
    return SourceCitation(
        doc_id="abc123456789",
        source_file="it_security.pdf",
        page_number=1,
        section_heading="Access Control",
        exact_quote="Employees must use MFA for all corporate logins.",
    )


def _sample_plan_dict():
    citation = _sample_citation().model_dump()
    return {
        "plan_id": "PLAN-SEC-01",
        "target_role": "Software Engineer",
        "title": "IT Security Onboarding Plan",
        "summary": "Mandatory security onboarding covering MFA and access control.",
        "prompt_version": "v1.0",
        "source_citation": citation,
        "modules": [
            {
                "module_id": "M1",
                "title": "Access & Authentication",
                "description": "Learn corporate authentication protocols.",
                "order_index": 1,
                "source_citation": citation,
                "tasks": [
                    {
                        "task_id": "T1.1",
                        "title": "Set up MFA",
                        "description": "Enroll in company MFA authenticator.",
                        "estimated_minutes": 30,
                        "source_citation": citation,
                    }
                ],
                "quizzes": [
                    {
                        "question_id": "Q1",
                        "question_text": "What is required for all corporate logins?",
                        "options": ["A. MFA", "B. Single password", "C. SMS only", "D. None"],
                        "correct_answer": "A. MFA",
                        "explanation": "Policy mandates MFA for corporate logins.",
                        "source_citation": citation,
                    }
                ],
            }
        ],
    }


# ---------------------------------------------------------------------------
# Response Schema Tests
# ---------------------------------------------------------------------------

class TestResponseSchemas:
    def test_valid_onboarding_plan_schema(self):
        plan = OnboardingPlanSchema.model_validate(_sample_plan_dict())
        assert plan.plan_id == "PLAN-SEC-01"
        assert len(plan.modules) == 1
        assert plan.modules[0].tasks[0].task_id == "T1.1"
        assert plan.modules[0].quizzes[0].question_id == "Q1"

    def test_citation_requires_int_page_number(self):
        with pytest.raises(ValidationError):
            SourceCitation(
                doc_id="abc",
                source_file="test.pdf",
                page_number="not_an_int",
                section_heading="Intro",
                exact_quote="Text",
            )

    def test_missing_source_citation_raises_error(self):
        bad_task = {
            "task_id": "T1",
            "title": "No Citation Task",
            "description": "Missing grounding",
            "estimated_minutes": 15,
        }
        with pytest.raises(ValidationError):
            TaskSchema.model_validate(bad_task)


# ---------------------------------------------------------------------------
# Prompt Registry Tests
# ---------------------------------------------------------------------------

class TestPromptRegistry:
    def test_get_onboarding_plan_template(self):
        template = get_prompt_template("onboarding_plan", "v1.0")
        assert "{target_role}" in template
        assert "{document_chunks}" in template

    def test_get_quiz_template(self):
        template = get_prompt_template("quiz_generation", "v1.0")
        assert "{module_content}" in template

    def test_nonexistent_template_raises(self):
        with pytest.raises(TemplateNotFoundError):
            get_prompt_template("unknown_template", "v1.0")

    def test_render_prompt_substitutes_values(self):
        rendered, version = render_prompt(
            "onboarding_plan",
            "v1.0",
            target_role="Data Analyst",
            document_chunks="Chunk sample text",
        )
        assert version == "v1.0"
        assert "Data Analyst" in rendered
        assert "Chunk sample text" in rendered


# ---------------------------------------------------------------------------
# Plan Generator Tests
# ---------------------------------------------------------------------------

class TestPlanGenerator:
    def test_empty_chunks_raises_value_error(self):
        with pytest.raises(ValueError, match="doc_chunks"):
            generate_onboarding_plan([], role="Developer")

    def test_empty_role_raises_value_error(self):
        chunk = DocumentChunk(
            doc_id="doc1",
            chunk_id="chk1",
            section_id=1,
            heading="Policy",
            page_number=1,
            content="Sample policy content over 80 characters long for valid testing purposes.",
            source_file="policy.pdf",
        )
        with pytest.raises(ValueError, match="role"):
            generate_onboarding_plan([chunk], role="")

    @patch("src.genai_pipeline.plan_generator.generate_content_with_retry")
    def test_generate_onboarding_plan_success(self, mock_generate):
        mock_generate.return_value = json.dumps(_sample_plan_dict())
        chunk = DocumentChunk(
            doc_id="doc1",
            chunk_id="chk1",
            section_id=1,
            heading="Access Control",
            page_number=1,
            content="Employees must use MFA for all corporate logins.",
            source_file="it_security.pdf",
        )
        plan = generate_onboarding_plan([chunk], role="Software Engineer")
        assert plan.plan_id == "PLAN-SEC-01"
        assert plan.target_role == "Software Engineer"
        assert plan.prompt_version == "v1.0"
        assert len(plan.modules) == 1


# ---------------------------------------------------------------------------
# Quiz Generator Tests
# ---------------------------------------------------------------------------

class TestQuizGenerator:
    def test_empty_content_raises_value_error(self):
        with pytest.raises(ValueError, match="module_content"):
            generate_quiz("")

    @patch("src.genai_pipeline.quiz_generator.generate_content_with_retry")
    def test_generate_quiz_success(self, mock_generate):
        sample_quiz = {
            "questions": [
                {
                    "question_id": "Q1",
                    "question_text": "What does MFA stand for?",
                    "options": [
                        "A. Multi-Factor Authentication",
                        "B. Main File Access",
                        "C. Master First Admin",
                        "D. Multi Fast Auth",
                    ],
                    "correct_answer": "A. Multi-Factor Authentication",
                    "explanation": "Standard security abbreviation.",
                    "source_citation": _sample_citation().model_dump(),
                }
            ]
        }
        mock_generate.return_value = json.dumps(sample_quiz)
        questions = generate_quiz("Policy text on multi-factor authentication.")
        assert len(questions) == 1
        assert questions[0].question_id == "Q1"


# ---------------------------------------------------------------------------
# Gemini Client Tests
# ---------------------------------------------------------------------------

class TestGeminiClient:
    def test_missing_api_key_raises(self, monkeypatch):
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        with pytest.raises(GeminiAPIError, match="GEMINI_API_KEY"):
            configure_client()
