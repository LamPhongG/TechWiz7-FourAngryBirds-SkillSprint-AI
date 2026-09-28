from src.schemas.comparison_contract import (
    ContradictionFlag,
    HallucinationFlag,
    SecurityThreatFlag,
    VerificationStatus,
)


def classify_verification_status(
    match_score: float,
    hallucinations: list[HallucinationFlag],
    contradictions: list[ContradictionFlag],
    security_threats: list[SecurityThreatFlag] | None = None,
) -> tuple[VerificationStatus, str]:
    """Classify the review decision into one of three statuses."""
    if security_threats:
        threats = [s.pattern_matched for s in security_threats[:2]]
        return (
            VerificationStatus.MANUAL_REVIEW_REQUIRED,
            f"Blocked by {len(security_threats)} security threat(s): {'; '.join(threats)}",
        )

    if hallucinations:
        reasons = [h.reason for h in hallucinations[:2]]
        return (
            VerificationStatus.MANUAL_REVIEW_REQUIRED,
            f"Blocked by {len(hallucinations)} hallucination flag(s): {'; '.join(reasons)}",
        )

    if contradictions:
        topics = [c.topic for c in contradictions[:2]]
        return (
            VerificationStatus.MANUAL_REVIEW_REQUIRED,
            f"Blocked by {len(contradictions)} policy contradiction(s): {'; '.join(topics)}",
        )

    if match_score < 0.75:
        return (
            VerificationStatus.MANUAL_REVIEW_REQUIRED,
            f"Match score too low ({match_score:.1%}), below 75% threshold.",
        )

    if match_score < 0.90:
        return (
            VerificationStatus.VERIFIED_WITH_WARNING,
            f"Verified with minor differences. Match score is {match_score:.1%}.",
        )

    return (
        VerificationStatus.VERIFIED,
        f"Fully verified across both pipelines. Match score is {match_score:.1%}.",
    )
