"""Generation Consistency Score.

Compares repeated runs of generation with identical input by business structure (cited sources,
module/task counts, matching question IDs). Pure Python comparison logic.
"""
from src.genai_pipeline.response_schemas import OnboardingPlanSchema

DOC_WEIGHT = 0.4
MODULE_WEIGHT = 0.2
TASK_WEIGHT = 0.2
QUESTION_WEIGHT = 0.2


def _doc_ids(plan: OnboardingPlanSchema) -> set[str]:
    ids = {plan.source_citation.doc_id}
    ids.update(module.source_citation.doc_id for module in plan.modules)
    return ids


def _jaccard(a: set, b: set) -> float:
    if not a and not b:
        return 1.0
    union = a | b
    return len(a & b) / len(union) if union else 1.0


def _count_similarity(a: int, b: int) -> float:
    if a == 0 and b == 0:
        return 1.0
    return 1 - abs(a - b) / max(a, b)


def calculate_consistency_score(plan_a: OnboardingPlanSchema, plan_b: OnboardingPlanSchema) -> dict:
    """Return `{consistency_score (0-100), matched_doc_ids, mismatched_doc_ids, module_count_diff}`."""
    doc_ids_a, doc_ids_b = _doc_ids(plan_a), _doc_ids(plan_b)
    question_ids_a = {q.question_id for m in plan_a.modules for q in m.quizzes}
    question_ids_b = {q.question_id for m in plan_b.modules for q in m.quizzes}
    task_count_a = sum(len(m.tasks) for m in plan_a.modules)
    task_count_b = sum(len(m.tasks) for m in plan_b.modules)

    raw_score = (
        DOC_WEIGHT * _jaccard(doc_ids_a, doc_ids_b)
        + MODULE_WEIGHT * _count_similarity(len(plan_a.modules), len(plan_b.modules))
        + TASK_WEIGHT * _count_similarity(task_count_a, task_count_b)
        + QUESTION_WEIGHT * _jaccard(question_ids_a, question_ids_b)
    )

    return {
        "consistency_score": round(raw_score * 100, 1),
        "matched_doc_ids": sorted(doc_ids_a & doc_ids_b),
        "mismatched_doc_ids": sorted(doc_ids_a ^ doc_ids_b),
        "module_count_diff": abs(len(plan_a.modules) - len(plan_b.modules)),
    }
