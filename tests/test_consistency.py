# Unit tests for generation consistency scoring.

from src.comparison_engine.consistency import calculate_consistency_score
from src.genai_pipeline.response_schemas import (
    ModuleSchema,
    OnboardingPlanSchema,
    QuizQuestionSchema,
    SourceCitation,
    TaskSchema,
)


def _citation(doc_id: str) -> SourceCitation:
    return SourceCitation(doc_id=doc_id, source_file=f"{doc_id}.pdf", page_number=1,
                          section_heading="Overview", exact_quote="n/a")


def _module(doc_id: str, n_tasks: int, question_ids: list[str]) -> ModuleSchema:
    citation = _citation(doc_id)
    return ModuleSchema(
        module_id=f"M-{doc_id}", title=doc_id, description=doc_id, order_index=1, source_citation=citation,
        tasks=[TaskSchema(task_id=f"T{i}", title="Task", description="Task", estimated_minutes=10,
                          source_citation=citation) for i in range(n_tasks)],
        quizzes=[QuizQuestionSchema(question_id=qid, question_text="Q?", options=["A", "B"],
                                    correct_answer="A", explanation="n/a", source_citation=citation)
                for qid in question_ids],
    )


def _plan(doc_ids: list[str], n_tasks: int = 1, question_ids: list[str] | None = None) -> OnboardingPlanSchema:
    question_ids = question_ids if question_ids is not None else ["Q1"]
    return OnboardingPlanSchema(
        plan_id="PLAN-1", target_role="DevOps Engineer", title="T", summary="S", prompt_version="v1.0",
        source_citation=_citation(doc_ids[0]),
        modules=[_module(doc_id, n_tasks, question_ids) for doc_id in doc_ids],
    )


def test_identical_plans_score_100():
    plan = _plan(["doc1", "doc2"], n_tasks=2, question_ids=["Q1", "Q2"])

    result = calculate_consistency_score(plan, plan)

    assert result["consistency_score"] == 100.0
    assert result["mismatched_doc_ids"] == []
    assert result["module_count_diff"] == 0


def test_completely_different_plans_score_low():
    # Differs in citations, module count, and questions — not just wording.
    plan_a = _plan(["doc1", "doc2"], n_tasks=1, question_ids=["Q1"])
    plan_b = _plan(["doc3", "doc4", "doc5"], n_tasks=3, question_ids=["Q9"])

    result = calculate_consistency_score(plan_a, plan_b)

    assert result["consistency_score"] < 30.0
    assert set(result["mismatched_doc_ids"]) == {"doc1", "doc2", "doc3", "doc4", "doc5"}


def test_partial_overlap_scores_between_full_and_none():
    plan_a = _plan(["doc1", "doc2"], question_ids=["Q1"])
    plan_b = _plan(["doc1", "doc3"], question_ids=["Q1"])

    result = calculate_consistency_score(plan_a, plan_b)

    assert 0.0 < result["consistency_score"] < 100.0
    assert result["matched_doc_ids"] == ["doc1"]
    assert set(result["mismatched_doc_ids"]) == {"doc2", "doc3"}


def test_module_count_diff_reflects_structural_drift():
    plan_a = _plan(["doc1"])
    plan_b = _plan(["doc1", "doc2", "doc3"])

    result = calculate_consistency_score(plan_a, plan_b)

    assert result["module_count_diff"] == 2
