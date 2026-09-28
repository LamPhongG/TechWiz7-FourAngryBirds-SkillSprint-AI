"""Weak-Area Detection (SRS Step 55-56): quiz_attempts -> weak_areas + manager_review_required.

Pure function, tested with mock objects (SimpleNamespace matching shape of real QuizAttempt:
module_id/score/total) — no DB or submission endpoint needed.
"""
from types import SimpleNamespace

from app.rule_pipeline.weak_areas import analyze_weak_areas


def _attempt(module_id: str, score: int, total: int) -> SimpleNamespace:
    return SimpleNamespace(module_id=module_id, score=score, total=total)


def _stages(*module_id_title_pairs: tuple[str, str]) -> list[dict]:
    modules = [{"id": mid, "title": title} for mid, title in module_id_title_pairs]
    return [{"key": "day1", "modules": modules}]


def test_module_below_threshold_is_flagged_weak():
    attempts = [_attempt("M1", 2, 10)]  # 20% correct
    stages = _stages(("M1", "Data Privacy Basics"))

    result = analyze_weak_areas(attempts, stages)

    assert result["manager_review_required"] is True
    assert result["weak_areas"] == [{"module_id": "M1", "topic": "Data Privacy Basics", "accuracy": 0.2}]


def test_module_at_or_above_threshold_is_not_flagged():
    attempts = [_attempt("M1", 8, 10)]  # 80% correct, default 70% threshold
    stages = _stages(("M1", "Data Privacy Basics"))

    result = analyze_weak_areas(attempts, stages)

    assert result["weak_areas"] == []
    assert result["manager_review_required"] is False


def test_multiple_attempts_on_same_module_are_aggregated():
    attempts = [_attempt("M1", 1, 5), _attempt("M1", 1, 5)]  # aggregated: 2/10 = 20%
    stages = _stages(("M1", "Security Basics"))

    result = analyze_weak_areas(attempts, stages)

    assert result["weak_areas"][0]["accuracy"] == 0.2


def test_module_missing_from_stages_falls_back_to_module_id_as_topic():
    attempts = [_attempt("M-GONE", 0, 5)]

    result = analyze_weak_areas(attempts, stages=[])

    assert result["weak_areas"] == [{"module_id": "M-GONE", "topic": "M-GONE", "accuracy": 0.0}]


def test_custom_threshold_is_respected():
    attempts = [_attempt("M1", 6, 10)]  # 60% correct
    stages = _stages(("M1", "X"))

    assert analyze_weak_areas(attempts, stages, threshold=0.5)["weak_areas"] == []
    assert analyze_weak_areas(attempts, stages, threshold=0.7)["manager_review_required"] is True


def test_no_attempts_means_no_weak_areas():
    assert analyze_weak_areas([], stages=[]) == {"weak_areas": [], "manager_review_required": False}
