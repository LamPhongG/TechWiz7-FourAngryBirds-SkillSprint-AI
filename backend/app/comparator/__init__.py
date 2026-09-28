"""Dual-pipeline comparison: field diff, hallucination and contradiction detection, final status.
SRS Step 46, 47 & Table 1.
"""
from app.comparator.engine import compare_path_with_ground_truth

__all__ = ["compare_path_with_ground_truth"]
