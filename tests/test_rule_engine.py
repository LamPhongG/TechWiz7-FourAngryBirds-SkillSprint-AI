# Unit tests for rule engine: coverage_scorer and prerequisite_checker.
# Engine is pure Python with no external AI SDK dependencies.

import ast
from pathlib import Path

from src.genai_pipeline.response_schemas import (
    ModuleSchema,
    OnboardingPlanSchema,
    SourceCitation,
)
from src.python_validation.coverage_scorer import (
    build_rule_data,
    calculate_coverage_score,
    load_role_matrix,
)
from src.python_validation.prerequisite_checker import check_prerequisites

MATRIX_ROWS = load_role_matrix()

AI_SDK_MODULES = {"google", "google_generativeai", "openai", "anthropic"}
RULE_ENGINE_FILES = [
    Path("src/python_validation/coverage_scorer.py"),
    Path("src/python_validation/prerequisite_checker.py"),
]


def _citation() -> SourceCitation:
    return SourceCitation(
        doc_id="doc1", source_file="policy.pdf", page_number=1,
        section_heading="Overview", exact_quote="n/a",
    )


def _plan(role: str, module_specs: list[tuple[str, int]]) -> OnboardingPlanSchema:
    """module_specs: list of (title, order_index); each module uses title for description."""
    citation = _citation()
    modules = [
        ModuleSchema(
            module_id=f"M{i}", title=title, description=title, order_index=order_index,
            source_citation=citation, tasks=[], quizzes=[],
        )
        for i, (title, order_index) in enumerate(module_specs)
    ]
    return OnboardingPlanSchema(
        plan_id="PLAN-TEST", target_role=role, title="Test Plan", summary="Test summary",
        prompt_version="v1.0", source_citation=citation, modules=modules,
    )


# ---------------------------------------------------------------------------
# Role Requirement Matrix (CSV)
# ---------------------------------------------------------------------------

def test_load_role_matrix_has_expected_columns():
    assert MATRIX_ROWS
    expected_columns = {"role", "topic", "mandatory", "priority", "max_total_minutes", "prerequisite_of"}
    assert expected_columns <= MATRIX_ROWS[0].keys()


# ---------------------------------------------------------------------------
# coverage_scorer.build_rule_data / calculate_coverage_score
# ---------------------------------------------------------------------------

def test_build_rule_data_matches_existing_hidden_test_scenario():
    """DevOps Engineer scenario used by hidden_test_ready with required_topics=[VPN, Encryption],
    max_total_minutes=240 — new matrix must not break this existing scenario."""
    rule_data = build_rule_data("DevOps Engineer", MATRIX_ROWS)

    assert set(rule_data["required_topics"]) == {"VPN", "Encryption"}
    assert rule_data["max_total_minutes"] == 240
    assert rule_data["is_new_role"] is False


def test_build_rule_data_unknown_role_is_flagged_not_silently_passed():
    rule_data = build_rule_data("Astronaut", MATRIX_ROWS)

    assert rule_data["required_topics"] == []
    assert rule_data["is_new_role"] is True


def test_calculate_coverage_score_partial_and_full():
    full_plan = _plan("DevOps Engineer", [("VPN Setup Guide", 1), ("Disk Encryption Basics", 2)])
    partial_plan = _plan("DevOps Engineer", [("VPN Setup Guide", 1)])

    assert calculate_coverage_score(full_plan, MATRIX_ROWS, "DevOps Engineer") == 1.0
    assert calculate_coverage_score(partial_plan, MATRIX_ROWS, "DevOps Engineer") == 0.5


def test_calculate_coverage_score_unknown_role_defaults_to_full():
    # Missing matrix data is not a plan content error (same convention as
    # backend/app/rule_pipeline/coverage.py::score_requirements when there are no mandatory requirements).
    plan = _plan("Astronaut", [("Anything", 1)])

    assert calculate_coverage_score(plan, MATRIX_ROWS, "Astronaut") == 1.0


# ---------------------------------------------------------------------------
# prerequisite_checker.check_prerequisites
# ---------------------------------------------------------------------------

def test_check_prerequisites_detects_wrong_order():
    wrong_order = _plan("DevOps Engineer", [("Disk Encryption Basics", 1), ("VPN Setup Guide", 2)])

    errors = check_prerequisites(wrong_order, MATRIX_ROWS, "DevOps Engineer")

    assert errors
    assert "VPN" in errors[0] and "Encryption" in errors[0]


def test_check_prerequisites_passes_correct_order():
    correct_order = _plan("DevOps Engineer", [("VPN Setup Guide", 1), ("Disk Encryption Basics", 2)])

    assert check_prerequisites(correct_order, MATRIX_ROWS, "DevOps Engineer") == []


def test_check_prerequisites_skips_topics_missing_from_plan():
    # VPN not yet in plan: coverage_scorer reports missing topics elsewhere, do not duplicate here.
    plan = _plan("DevOps Engineer", [("Disk Encryption Basics", 1)])

    assert check_prerequisites(plan, MATRIX_ROWS, "DevOps Engineer") == []


def test_check_prerequisites_unknown_role_has_nothing_to_check():
    plan = _plan("Astronaut", [("Anything", 1)])

    assert check_prerequisites(plan, MATRIX_ROWS, "Astronaut") == []


# ---------------------------------------------------------------------------
# Anti-AI-signature: rule engine must not depend on any AI SDK
# ---------------------------------------------------------------------------

def test_rule_engine_modules_do_not_import_any_ai_sdk():
    for path in RULE_ENGINE_FILES:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imported_roots: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_roots.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported_roots.add(node.module.split(".")[0])

        assert not (imported_roots & AI_SDK_MODULES), f"{path} imports an AI SDK: {imported_roots & AI_SDK_MODULES}"
