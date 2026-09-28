"""Pure Python rule pipeline: reads Role Requirement Matrix and computes coverage score.

Coverage score is evaluated independently from GenAI generation.
"""
import csv
from pathlib import Path

from src.genai_pipeline.response_schemas import OnboardingPlanSchema

DEFAULT_MATRIX_PATH = Path(__file__).resolve().parent.parent / "role_matrix" / "role_matrix.csv"


def load_role_matrix(csv_path: Path | str = DEFAULT_MATRIX_PATH) -> list[dict]:
    """Read role_matrix.csv into a list of dicts (1 dict = 1 row = 1 role-topic pair)."""
    with open(csv_path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def _rows_for_role(role: str, matrix_rows: list[dict]) -> list[dict]:
    return [r for r in matrix_rows if r["role"].strip().lower() == role.strip().lower()]


def build_rule_data(role: str, matrix_rows: list[dict]) -> dict:
    """Build `rule_data` for ComparisonEngine.compare() from the real matrix instead of hardcoded dicts.

    Roles not in the matrix are treated as unmapped:
    `required_topics` is empty and `is_new_role=True` so caller routes to manual review rather than assuming no requirements.
    """
    role_rows = _rows_for_role(role, matrix_rows)
    if not role_rows:
        return {"role": role, "required_topics": [], "max_total_minutes": 480, "is_new_role": True}

    mandatory_topics = [r["topic"] for r in role_rows if r.get("mandatory", "Yes").strip().lower() == "yes"]
    max_minutes = int(role_rows[0].get("max_total_minutes") or 480)
    return {"role": role, "required_topics": mandatory_topics, "max_total_minutes": max_minutes, "is_new_role": False}


def _plan_corpus(plan: OnboardingPlanSchema) -> str:
    fragments = [plan.title, plan.summary]
    for module in plan.modules:
        fragments += [module.title, module.description]
        fragments += [t.title for t in module.tasks] + [t.description for t in module.tasks]
        fragments += [q.question_text for q in module.quizzes]
    return " ".join(fragments).lower()


def calculate_coverage_score(plan: OnboardingPlanSchema, matrix_rows: list[dict], role: str) -> float:
    """Coverage Score = mandatory topics appearing in plan / total mandatory topics.

    No mandatory topics (role not in matrix) -> 1.0: missing source data is not a plan content error,
    matching convention in backend/app/rule_pipeline/coverage.py.
    """
    required_topics = build_rule_data(role, matrix_rows)["required_topics"]
    if not required_topics:
        return 1.0

    corpus = _plan_corpus(plan)
    covered = sum(1 for topic in required_topics if topic.lower() in corpus)
    return round(covered / len(required_topics), 3)
