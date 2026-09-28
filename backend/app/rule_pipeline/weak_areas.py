"""Weak-area learning detection from quiz performance.

Aggregates quiz attempts by module, computes correct answer ratios;
modules below threshold are identified as weak areas for reinforcement.
"""
from typing import Protocol

WEAK_AREA_THRESHOLD = 0.7


class QuizAttemptLike(Protocol):
    module_id: str
    score: int
    total: int


def _module_titles(stages: list[dict]) -> dict[str, str]:
    return {
        module.get("id"): module.get("title", module.get("id"))
        for stage in stages
        for module in stage.get("modules", [])
    }


def analyze_weak_areas(
    attempts: list[QuizAttemptLike], stages: list[dict], threshold: float = WEAK_AREA_THRESHOLD
) -> dict:
    """Returns `{weak_areas: [{module_id, topic, accuracy}], manager_review_required: bool}`.

    `topic` is derived from module titles. Modules without attempts are skipped.
    """
    totals: dict[str, list[int]] = {}
    for attempt in attempts:
        bucket = totals.setdefault(attempt.module_id, [0, 0])
        bucket[0] += attempt.score
        bucket[1] += attempt.total

    module_titles = _module_titles(stages)
    weak_areas = []
    for module_id, (score, total) in totals.items():
        if total == 0:
            continue
        accuracy = score / total
        if accuracy < threshold:
            weak_areas.append({
                "module_id": module_id,
                "topic": module_titles.get(module_id, module_id),
                "accuracy": round(accuracy, 3),
            })

    return {"weak_areas": weak_areas, "manager_review_required": bool(weak_areas)}
