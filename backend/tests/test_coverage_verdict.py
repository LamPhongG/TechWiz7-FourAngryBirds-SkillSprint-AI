"""How coverage feeds the final verification status (SRS 1.2: Verified only with every mandatory requirement covered)."""
from types import SimpleNamespace

from app.models import FinalStatus, PathPurpose
from app.services.path_checks import run_checks


def _reasons(coverage):
    path = SimpleNamespace(purpose=PathPurpose.ONBOARDING, stages=[], coverage=coverage, excluded_chunks=[])
    result = run_checks(path, [], {})
    return {r["key"]: r.get("vars") for r in result.reasons}, result


def test_ninety_percent_is_a_warning_not_verified():
    reasons, _ = _reasons({"score": 0.9, "counts": {"required": 10}})
    assert reasons["reason_medium_coverage"] == {"score": 90, "min": 100}


def test_below_sixty_percent_needs_manual_review():
    reasons, result = _reasons({"score": 0.5, "counts": {"required": 4}})
    assert reasons["reason_low_coverage"] == {"score": 50, "min": 60}
    assert result.final_status is FinalStatus.MANUAL_REVIEW


def test_full_coverage_adds_no_coverage_reason():
    reasons, _ = _reasons({"score": 1.0, "counts": {"required": 4}})
    assert not {"reason_low_coverage", "reason_medium_coverage", "reason_coverage_pending", "reason_matrix_empty"} & set(reasons)


def test_empty_matrix_needs_manual_review():
    reasons, result = _reasons({"score": None, "counts": {"required": 0}})
    assert "reason_matrix_empty" in reasons and "reason_coverage_pending" not in reasons
    assert result.final_status is FinalStatus.MANUAL_REVIEW


def test_missing_coverage_is_pending():
    reasons, _ = _reasons(None)
    assert "reason_coverage_pending" in reasons
