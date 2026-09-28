"""GenAI Consistency Testing & Scoring Engine.

Executes repeated structured generations under controlled parameters and evaluates
consistency of structured business outputs (mandatory requirements, cited sources,
module categories, and assessment topics).
"""

from typing import Any
from src.document_processing.chunker import DocumentChunk
from src.genai_pipeline.plan_generator import generate_onboarding_plan
from src.genai_pipeline.response_schemas import OnboardingPlanSchema


def run_consistency_generations(
    doc_chunks: list[DocumentChunk],
    role: str,
    runs: int = 2,
    prompt_version: str = "v1.0",
) -> list[OnboardingPlanSchema]:
    """Execute the generation task multiple times using controlled parameters."""
    if runs < 2:
        raise ValueError("Consistency check requires at least 2 runs.")

    generated_plans: list[OnboardingPlanSchema] = []
    for _ in range(runs):
        plan = generate_onboarding_plan(
            doc_chunks=doc_chunks,
            role=role,
            prompt_version=prompt_version,
        )
        generated_plans.append(plan)
    return generated_plans


def _extract_plan_signature(plan: OnboardingPlanSchema) -> dict[str, Any]:
    """Extract structured business features from a plan for deterministic comparison."""
    # 1. Source files cited across plan and modules
    sources = {plan.source_citation.source_file.strip().lower()}
    for m in plan.modules:
        if m.source_citation.source_file:
            sources.add(m.source_citation.source_file.strip().lower())
        for t in m.tasks:
            if t.source_citation.source_file:
                sources.add(t.source_citation.source_file.strip().lower())
        for q in m.quizzes:
            if q.source_citation.source_file:
                sources.add(q.source_citation.source_file.strip().lower())

    # 2. Module titles normalized
    module_titles = {m.title.strip().lower() for m in plan.modules}

    # 3. Task titles normalized
    task_titles = {t.title.strip().lower() for m in plan.modules for t in m.tasks}

    # 4. Total task count
    total_tasks = sum(len(m.tasks) for m in plan.modules)

    return {
        "sources": sources,
        "modules": module_titles,
        "tasks": task_titles,
        "total_tasks": total_tasks,
    }


def calculate_consistency_score(plans: list[OnboardingPlanSchema]) -> dict[str, Any]:
    """Calculate structured consistency score between repeated generations.
    
    The comparison focuses on structured business requirements rather than exact wording:
    - 40% Source document consistency
    - 35% Module/topic category overlap
    - 25% Task volume and structure stability
    """
    if not plans or len(plans) < 2:
        return {
            "consistency_score": 1.0,
            "is_consistent": True,
            "runs_evaluated": len(plans),
            "discrepancies": [],
            "common_sources": [],
            "common_topics": [],
        }

    signatures = [_extract_plan_signature(p) for p in plans]
    discrepancies: list[str] = []

    # 1. Source overlap (Jaccard similarity across runs)
    all_sources = set().union(*(s["sources"] for s in signatures))
    common_sources = set(signatures[0]["sources"])
    for s in signatures[1:]:
        common_sources.intersection_update(s["sources"])

    source_score = (len(common_sources) / len(all_sources)) if all_sources else 1.0
    if source_score < 0.8:
        missing_src = all_sources - common_sources
        discrepancies.append(f"Inconsistent source citations across runs: {list(missing_src)}")

    # 2. Module category / topic overlap
    # Keyword-based topic extraction
    def get_keywords(titles: set[str]) -> set[str]:
        words = set()
        for t in titles:
            for w in t.split():
                clean = "".join(ch for ch in w if ch.isalnum())
                if len(clean) > 3:
                    words.add(clean)
        return words

    kw_sets = [get_keywords(s["modules"]) for s in signatures]
    all_keywords = set().union(*kw_sets)
    common_keywords = set(kw_sets[0])
    for kws in kw_sets[1:]:
        common_keywords.intersection_update(kws)

    topic_score = (len(common_keywords) / len(all_keywords)) if all_keywords else 1.0
    if topic_score < 0.6:
        discrepancies.append("Significant topic discrepancy detected between repeated generations.")

    # 3. Task volume stability
    task_counts = [s["total_tasks"] for s in signatures]
    min_tasks, max_tasks = min(task_counts), max(task_counts)
    task_ratio = (min_tasks / max_tasks) if max_tasks > 0 else 1.0
    if task_ratio < 0.7:
        discrepancies.append(f"Task volume variance across runs: {task_counts}")

    # Weighted final score
    consistency_score = round(0.40 * source_score + 0.35 * topic_score + 0.25 * task_ratio, 3)
    is_consistent = consistency_score >= 0.70 and len(discrepancies) == 0

    return {
        "consistency_score": consistency_score,
        "is_consistent": is_consistent,
        "runs_evaluated": len(plans),
        "source_consistency": round(source_score, 3),
        "topic_consistency": round(topic_score, 3),
        "task_consistency": round(task_ratio, 3),
        "common_sources": sorted(list(common_sources)),
        "common_topics": sorted(list(common_keywords)),
        "discrepancies": discrepancies,
    }
