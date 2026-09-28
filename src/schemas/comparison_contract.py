from enum import Enum
from typing import Any
from pydantic import BaseModel


class VerificationStatus(str, Enum):
    VERIFIED = "VERIFIED"
    VERIFIED_WITH_WARNING = "VERIFIED_WITH_WARNING"
    MANUAL_REVIEW_REQUIRED = "MANUAL_REVIEW_REQUIRED"


class ComparisonItem(BaseModel):
    field_name: str
    pipeline1_value: Any
    pipeline2_value: Any
    is_match: bool
    confidence_score: float = 1.0
    notes: str = ""


class HallucinationFlag(BaseModel):
    item_id: str
    field_name: str
    claimed_text: str
    reason: str
    severity: str = "HIGH"


class ContradictionFlag(BaseModel):
    conflict_id: str
    topic: str
    statement_a: str
    statement_b: str
    source_reference: str
    severity: str = "HIGH"


class SecurityThreatFlag(BaseModel):
    threat_id: str
    pattern_matched: str
    excerpt: str
    severity: str = "CRITICAL"


class ComparisonReport(BaseModel):
    report_id: str
    doc_id: str
    target_role: str
    status: VerificationStatus
    match_score: float
    total_checks: int
    matched_checks: int
    items: list[ComparisonItem] = []
    hallucinations: list[HallucinationFlag] = []
    contradictions: list[ContradictionFlag] = []
    security_threats: list[SecurityThreatFlag] = []
    summary: str
