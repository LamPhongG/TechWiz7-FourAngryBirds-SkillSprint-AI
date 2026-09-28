"""Rule pipeline: document precedence rules, prerequisite checks, and weak-area detection.

Coverage score is computed in `app.services.role_matrix.compute_coverage`
using the Role Requirement Matrix.
"""
from app.rule_pipeline.precedence import precedence_tier, resolve_precedence, sort_by_precedence
from app.rule_pipeline.weak_areas import analyze_weak_areas

__all__ = [
    "analyze_weak_areas",
    "precedence_tier",
    "resolve_precedence",
    "sort_by_precedence",
]
