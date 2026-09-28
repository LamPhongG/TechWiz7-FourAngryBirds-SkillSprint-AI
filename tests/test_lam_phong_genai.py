"""Unit tests for Chau Quoc Lam Phong's GenAI Pipeline modules:
- Assessment Rubrics (Step 24)
- Difficulty Levels (Step 25)
- GenAI Consistency Scoring (Step 44 & 45)
- Selective Regeneration (Step 59)
"""

import json
from unittest.mock import patch
import pytest

from src.document_processing.chunker import DocumentChunk
from src.genai_pipeline.consistency_checker import calculate_consistency_score
from src.genai_pipeline.response_schemas import (
    ModuleSchema,
    OnboardingPlanSchema,
    QuizQuestionSchema,
    RubricCriterionSchema,
    SourceCitation,
    TaskSchema,
)
from src.genai_pipeline.selective_regenerator import (
    RegeneratedModulesResponse,
    regenerate_affected_modules,
)


def _sample_citation():
    return SourceCitation(
        doc_id="DOC-11",
        source_file="DOC-11_sop-employee-onboarding_v1.0.pdf",
        page_number=1,
        section_heading="Onboarding Standards",
        exact_quote="New hires must complete orientation within the first 14 days.",
    )


def _create_mock_plan(plan_id="PLAN-001", role="DevOps Engineer"):
    cit = _sample_citation()
    rubric_item = RubricCriterionSchema(
        criterion="Pipeline Deployment Execution",
        weight=0.5,
        expected_performance="Deploys containerized service to staging with 0 downtime.",
        pass_condition="Passes automated health checks and SLA criteria.",
    )

    m1 = ModuleSchema(
        module_id="MOD-01",
        title="CI/CD Fundamentals",
        description="Introduction to corporate deployment pipelines.",
        order_index=1,
        difficulty="Beginner",
        tasks=[
            TaskSchema(
                task_id="TSK-01",
                title="Configure CI Runner",
                description="Set up local gitlab runner.",
                estimated_minutes=45,
                difficulty="Beginner",
                source_citation=cit,
            )
        ],
        quizzes=[
            QuizQuestionSchema(
                question_id="Q-01",
                question_text="What is the maximum allowed deployment window?",
                options=["15 minutes", "30 minutes", "1 hour", "2 hours"],
                correct_answer="30 minutes",
                explanation="Policy SOP-01 stipulates 30m maximum maintenance window.",
                difficulty="Beginner",
                source_citation=cit,
            )
        ],
        rubric=[],
        source_citation=cit,
    )

    m2 = ModuleSchema(
        module_id="MOD-02",
        title="Production Incident Response",
        description="Escalation protocol for high-severity outages.",
        order_index=2,
        difficulty="Advanced",
        tasks=[
            TaskSchema(
                task_id="TSK-02",
                title="Execute Rollback Drill",
                description="Perform zero-loss rollback on simulated failure.",
                estimated_minutes=60,
                difficulty="Advanced",
                source_citation=cit,
            )
        ],
        quizzes=[
            QuizQuestionSchema(
                question_id="Q-02",
                question_text="Who must be paged first upon P1 incident?",
                options=["Engineering Lead", "CEO", "Sales Director", "Office Manager"],
                correct_answer="Engineering Lead",
                explanation="Incident SOP designates Tech Lead as primary commander.",
                difficulty="Advanced",
                source_citation=cit,
            )
        ],
        rubric=[rubric_item],
        source_citation=cit,
    )

    return OnboardingPlanSchema(
        plan_id=plan_id,
        target_role=role,
        title="DevOps Onboarding Plan",
        summary="Structured 2-stage onboarding roadmap.",
        prompt_version="v1.0",
        modules=[m1, m2],
        source_citation=cit,
    )


# ---------------------------------------------------------------------------
# Test Step 24: Assessment Rubric
# ---------------------------------------------------------------------------

def test_assessment_rubric_schema():
    rubric = RubricCriterionSchema(
        criterion="Code Security Review",
        weight=0.3,
        expected_performance="Identifies all OWASP top 10 risks in PR",
        pass_condition="No unresolved high-severity vulnerabilities",
    )
    assert rubric.criterion == "Code Security Review"
    assert rubric.weight == 0.3
    assert "OWASP" in rubric.expected_performance
    assert "high-severity" in rubric.pass_condition


def test_module_with_rubric():
    plan = _create_mock_plan()
    assessment_mod = plan.modules[1]
    assert len(assessment_mod.rubric) == 1
    assert assessment_mod.rubric[0].criterion == "Pipeline Deployment Execution"
    assert assessment_mod.rubric[0].weight == 0.5


# ---------------------------------------------------------------------------
# Test Step 25: Difficulty Levels
# ---------------------------------------------------------------------------

def test_difficulty_levels():
    plan = _create_mock_plan()
    assert plan.modules[0].difficulty == "Beginner"
    assert plan.modules[0].tasks[0].difficulty == "Beginner"
    assert plan.modules[0].quizzes[0].difficulty == "Beginner"

    assert plan.modules[1].difficulty == "Advanced"
    assert plan.modules[1].tasks[0].difficulty == "Advanced"
    assert plan.modules[1].quizzes[0].difficulty == "Advanced"


# ---------------------------------------------------------------------------
# Test Step 44 & 45: GenAI Consistency Evaluation
# ---------------------------------------------------------------------------

def test_consistency_identical_plans():
    plan_a = _create_mock_plan("PLAN-A")
    plan_b = _create_mock_plan("PLAN-B")

    result = calculate_consistency_score([plan_a, plan_b])
    assert result["consistency_score"] >= 0.95
    assert result["is_consistent"] is True
    assert len(result["discrepancies"]) == 0
    assert result["runs_evaluated"] == 2


def test_consistency_differing_plans():
    cit_alt = SourceCitation(
        doc_id="DOC-99",
        source_file="DOC-99_unrelated_manual.pdf",
        page_number=10,
        section_heading="Miscellaneous",
        exact_quote="General notes.",
    )
    plan_a = _create_mock_plan("PLAN-A")

    # Plan B has totally different sources and topics
    m_diff = ModuleSchema(
        module_id="MOD-99",
        title="Cooking in Office Pantry",
        description="Pantry rules.",
        order_index=1,
        difficulty="Beginner",
        tasks=[],
        quizzes=[],
        rubric=[],
        source_citation=cit_alt,
    )
    plan_b = OnboardingPlanSchema(
        plan_id="PLAN-B",
        target_role="Chef",
        title="Office Pantry Plan",
        summary="Different content.",
        prompt_version="v1.0",
        modules=[m_diff],
        source_citation=cit_alt,
    )

    result = calculate_consistency_score([plan_a, plan_b])
    assert result["consistency_score"] < 0.70
    assert result["is_consistent"] is False
    assert len(result["discrepancies"]) > 0


# ---------------------------------------------------------------------------
# Test Step 59: Selective Regeneration
# ---------------------------------------------------------------------------

def test_selective_regeneration_preserves_unaffected_module():
    plan = _create_mock_plan()
    cit = _sample_citation()

    # Suppose MOD-01 needs regeneration with new content, MOD-02 should be preserved
    regenerated_mod_01 = ModuleSchema(
        module_id="MOD-01",
        title="Updated CI/CD with Kubernetes",
        description="Updated deployment procedures under new 2026 infra policy.",
        order_index=1,
        difficulty="Intermediate",
        tasks=[
            TaskSchema(
                task_id="TSK-01-V2",
                title="Deploy to K8s cluster",
                description="Execute kubectl rollout.",
                estimated_minutes=40,
                difficulty="Intermediate",
                source_citation=cit,
            )
        ],
        quizzes=[
            QuizQuestionSchema(
                question_id="Q-01-V2",
                question_text="What is the default deployment namespace?",
                options=["staging", "prod", "default", "kube-system"],
                correct_answer="staging",
                explanation="Policy SOP-02 requires staging namespace.",
                difficulty="Intermediate",
                source_citation=cit,
            )
        ],
        rubric=[],
        source_citation=cit,
    )

    fake_response = RegeneratedModulesResponse(modules=[regenerated_mod_01])

    with patch("src.genai_pipeline.selective_regenerator.generate_content_with_retry") as mock_gemini:
        mock_gemini.return_value = fake_response.model_dump_json()

        dummy_chunk = DocumentChunk(
            doc_id="DOC-11",
            chunk_id="CHK-1",
            section_id=1,
            heading="Infrastructure Update",
            page_number=2,
            content="Deployments must use Kubernetes staging namespace.",
            source_file="DOC-11_sop-employee-onboarding_v1.0.pdf",
        )

        updated_plan, report = regenerate_affected_modules(
            existing_plan=plan,
            affected_module_ids=["MOD-01"],
            updated_chunks=[dummy_chunk],
        )

        assert report["status"] == "success"
        assert report["regenerated_count"] == 1
        assert report["preserved_count"] == 1

        # MOD-01 should be updated
        assert updated_plan.modules[0].module_id == "MOD-01"
        assert updated_plan.modules[0].title == "Updated CI/CD with Kubernetes"

        # MOD-02 MUST remain completely intact and untouched!
        assert updated_plan.modules[1].module_id == "MOD-02"
        assert updated_plan.modules[1].title == "Production Incident Response"
        assert len(updated_plan.modules[1].rubric) == 1
