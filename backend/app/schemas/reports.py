"""Report rows for HR, Reviewers and Admins (SRS Step 51-53, 62). `None` means "no data yet", never zero."""
from datetime import datetime

from pydantic import BaseModel


class RoleCoverageRow(BaseModel):
    role_id: str
    role_name: str
    role_name_en: str
    department: str
    mandatory_requirements: int
    path_id: str | None
    path_title: str | None
    path_title_en: str | None
    covered_requirements: int | None
    # Percent 0-100 (SRS Step 29: covered mandatory requirements / total mandatory requirements).
    coverage_score: int | None
    traceability_score: int | None
    final_status: str | None


class QuizAnalyticsRow(BaseModel):
    path_id: str
    path_title: str
    path_title_en: str
    stage_key: str
    module_id: str
    module_title: str
    module_title_en: str
    quiz_count: int
    attempts: int
    pass_rate: int | None
    avg_score: int | None
    # no_attempts · weak (below the weak-area threshold) · ok
    status: str


class DocumentReportRow(BaseModel):
    id: str
    code: str
    title: str
    title_en: str
    category: str
    version: str
    lifecycle: str
    processing_status: str
    chunks_count: int
    referenced_in_paths: int
    cited_items: int
    # Percent of the items citing this document whose quote is found verbatim in it (knowledge check "verified").
    citation_accuracy: int | None


class AlertRow(BaseModel):
    id: str
    date: datetime | None
    # prompt_injection · hallucination · unsupported_answer · excluded_chunks
    type: str
    severity: str
    source: str
    details: str
    path_id: str | None
    status: str


class ComparisonSummaryRow(BaseModel):
    path_id: str
    path_title: str
    path_title_en: str
    role: str
    department: str | None
    status: str
    engine: str | None
    genai_claims_available: bool
    requirements: int
    matches: int
    mismatches: int
    missing: int
    unsupported: int
    coverage_score: int | None
    traceability_score: int | None
    consistency_score: int | None
    decision: str
