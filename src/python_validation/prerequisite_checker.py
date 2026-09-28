"""Pure Python rule pipeline: check prerequisite order between modules.
"""
from src.genai_pipeline.response_schemas import OnboardingPlanSchema


def _rows_with_prerequisite(role: str, matrix_rows: list[dict]) -> list[dict]:
    return [
        r for r in matrix_rows
        if r["role"].strip().lower() == role.strip().lower() and r.get("prerequisite_of", "").strip()
    ]


def check_prerequisites(plan: OnboardingPlanSchema, matrix_rows: list[dict], role: str) -> list[str]:
    """Return list of ordering errors (empty if valid).

    For each (prerequisite topic, dependent topic) pair declared in the matrix for this role:
    find module containing each topic (by title/description), then compare `order_index`.
    Pairs not yet present in plan are skipped (coverage_scorer reports missing topics elsewhere).
    """
    rows = _rows_with_prerequisite(role, matrix_rows)
    if not rows:
        return []

    module_order = {m.module_id: m.order_index for m in plan.modules}
    module_text = {m.module_id: f"{m.title} {m.description}".lower() for m in plan.modules}

    def _find_module(topic: str) -> str | None:
        needle = topic.strip().lower()
        return next((mid for mid, text in module_text.items() if needle in text), None)

    errors: list[str] = []
    for row in rows:
        prereq_module = _find_module(row["topic"])
        dependent_module = _find_module(row["prerequisite_of"])
        if prereq_module is None or dependent_module is None:
            continue
        if module_order[prereq_module] >= module_order[dependent_module]:
            errors.append(
                f"Module containing '{row['topic']}' (order_index={module_order[prereq_module]}) must be taken "
                f"before module containing '{row['prerequisite_of']}' (order_index={module_order[dependent_module]})"
            )
    return errors
