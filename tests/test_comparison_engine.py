# Unit tests for Comparison Engine, Hallucination Detector, and Contradiction Checker

from src.comparison_engine.classifier import classify_verification_status
from src.comparison_engine.engine import ComparisonEngine
from src.contradiction_checks.checker import check_contradictions
from src.document_processing.chunker import DocumentChunk
from src.hallucination_checks.detector import detect_hallucinations
from src.genai_pipeline.response_schemas import (
    ModuleSchema,
    OnboardingPlanSchema,
    QuizQuestionSchema,
    SourceCitation,
    TaskSchema,
)
from src.schemas.comparison_contract import (
    ContradictionFlag,
    HallucinationFlag,
    VerificationStatus,
)


# ---------------------------------------------------------------------------
# Test Fixtures & Helpers
# ---------------------------------------------------------------------------

def _make_chunk(content: str, chunk_id: str = "chk1", page: int = 1) -> DocumentChunk:
    return DocumentChunk(
        doc_id="doc100",
        chunk_id=chunk_id,
        section_id=1,
        heading="Security Policy",
        page_number=page,
        content=content,
        source_file="sec_policy.pdf",
    )


def _make_plan(quote: str, role: str = "Software Engineer", duration: int = 30) -> OnboardingPlanSchema:
    citation = SourceCitation(
        doc_id="doc100",
        source_file="sec_policy.pdf",
        page_number=1,
        section_heading="Security Policy",
        exact_quote=quote,
    )
    return OnboardingPlanSchema(
        plan_id="PLAN-001",
        target_role=role,
        title="Engineering Security Onboarding",
        summary="Security onboarding summary.",
        prompt_version="v1.0",
        source_citation=citation,
        modules=[
            ModuleSchema(
                module_id="M1",
                title="Password and Authentication",
                description="Overview of access policies.",
                order_index=1,
                source_citation=citation,
                tasks=[
                    TaskSchema(
                        task_id="T1.1",
                        title="Configure Password",
                        description="Setup password according to policy.",
                        estimated_minutes=duration,
                        source_citation=citation,
                    )
                ],
                quizzes=[
                    QuizQuestionSchema(
                        question_id="Q1",
                        question_text="How often should passwords be changed?",
                        options=["A. 30", "B. 60", "C. 90", "D. 180"],
                        correct_answer="C",
                        explanation="Every 90 days.",
                        source_citation=citation,
                    )
                ],
            )
        ],
    )


# ---------------------------------------------------------------------------
# Hallucination Detector Tests
# ---------------------------------------------------------------------------

class TestHallucinationDetector:
    def test_valid_quote_passes_without_flags(self):
        real_text = "All employees must change passwords every 90 days without exception."
        chunk = _make_chunk(real_text)
        plan = _make_plan(quote="All employees must change passwords every 90 days")

        flags = detect_hallucinations(plan, [chunk])
        assert len(flags) == 0

    def test_fabricated_quote_triggers_hallucination_flag(self):
        real_text = "All employees must change passwords every 90 days."
        chunk = _make_chunk(real_text)
        plan = _make_plan(quote="Employees are allowed to bring pets to the office on Fridays.")

        flags = detect_hallucinations(plan, [chunk])
        assert len(flags) >= 1
        assert flags[0].severity == "HIGH"
        assert "not found" in flags[0].reason


# ---------------------------------------------------------------------------
# Contradiction Checker Tests
# ---------------------------------------------------------------------------

class TestContradictionChecker:
    def test_consistent_policy_has_no_contradictions(self):
        chunk1 = _make_chunk("Passwords must be changed every 90 days.", "chk1")
        chunk2 = _make_chunk("MFA is mandatory for VPN access.", "chk2")
        flags = check_contradictions(doc_chunks=[chunk1, chunk2])
        assert len(flags) == 0

    def test_conflicting_numbers_trigger_contradiction_flag(self):
        # One chunk says 90 days, another chunk says 30 days
        chunk1 = _make_chunk("Passwords must be changed every 90 days.", "chk1")
        chunk2 = _make_chunk("Passwords expire every 30 days for security.", "chk2")

        flags = check_contradictions(doc_chunks=[chunk1, chunk2])
        assert len(flags) >= 1
        assert "Password Expiry" in flags[0].topic


# ---------------------------------------------------------------------------
# Classifier Decision Tests
# ---------------------------------------------------------------------------

class TestClassifier:
    def test_verified_when_high_score_and_no_flags(self):
        status, _ = classify_verification_status(0.95, [], [])
        assert status == VerificationStatus.VERIFIED

    def test_verified_with_warning_on_minor_mismatch(self):
        status, _ = classify_verification_status(0.85, [], [])
        assert status == VerificationStatus.VERIFIED_WITH_WARNING

    def test_manual_review_when_hallucination_exists(self):
        h_flag = HallucinationFlag(
            item_id="chk1",
            field_name="quote",
            claimed_text="invented quote",
            reason="not in text",
        )
        status, _ = classify_verification_status(0.95, [h_flag], [])
        assert status == VerificationStatus.MANUAL_REVIEW_REQUIRED

    def test_manual_review_when_contradiction_exists(self):
        c_flag = ContradictionFlag(
            conflict_id="C1",
            topic="Expiry",
            statement_a="90 days",
            statement_b="30 days",
            source_reference="chk1 vs chk2",
        )
        status, _ = classify_verification_status(0.95, [], [c_flag])
        assert status == VerificationStatus.MANUAL_REVIEW_REQUIRED

    def test_manual_review_when_score_too_low(self):
        status, _ = classify_verification_status(0.60, [], [])
        assert status == VerificationStatus.MANUAL_REVIEW_REQUIRED


# ---------------------------------------------------------------------------
# Comparison Engine End-to-End Tests
# ---------------------------------------------------------------------------

class TestComparisonEngine:
    def test_full_comparison_produces_verified_report(self):
        real_text = "All employees must change passwords every 90 days."
        chunk = _make_chunk(real_text)
        plan = _make_plan(quote="All employees must change passwords every 90 days")

        rule_data = {
            "role": "Software Engineer",
            "required_topics": ["Password"],
            "max_total_minutes": 120,
        }

        engine = ComparisonEngine()
        report = engine.compare(plan, rule_data, [chunk])

        assert report.status == VerificationStatus.VERIFIED
        assert report.match_score == 1.0
        assert report.matched_checks == report.total_checks
        assert len(report.hallucinations) == 0

    def test_full_comparison_with_missing_topic_lowers_score(self):
        real_text = "All employees must change passwords every 90 days."
        chunk = _make_chunk(real_text)
        plan = _make_plan(quote="All employees must change passwords every 90 days")

        rule_data = {
            "role": "Software Engineer",
            "required_topics": ["Password", "Financial Auditing"],  # Financial Auditing is missing in plan
            "max_total_minutes": 120,
        }

        engine = ComparisonEngine()
        report = engine.compare(plan, rule_data, [chunk])

        assert report.match_score < 1.0
        mismatches = [i for i in report.items if not i.is_match]
        assert len(mismatches) == 1
        assert "Financial Auditing" in mismatches[0].field_name
