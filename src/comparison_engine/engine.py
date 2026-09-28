import uuid
from src.comparison_engine.classifier import classify_verification_status
from src.contradiction_checks.checker import check_contradictions
from src.document_processing.chunker import DocumentChunk
from src.genai_pipeline.response_schemas import OnboardingPlanSchema
from src.schemas.comparison_contract import (
    ComparisonItem,
    ComparisonReport,
    SecurityThreatFlag,
)
from src.security.injection_filter import scan_for_prompt_injection


class ComparisonEngine:
    """Compare Pipeline 1 (GenAI plan) and Pipeline 2 (Rule engine output) field by field."""

    def compare(
        self,
        plan: OnboardingPlanSchema,
        rule_data: dict,
        doc_chunks: list[DocumentChunk],
    ) -> ComparisonReport:
        items: list[ComparisonItem] = []

        # 1. Check Target Role Alignment
        expected_role = rule_data.get("role", "").strip()
        role_matches = (
            expected_role.lower() in plan.target_role.lower()
            or plan.target_role.lower() in expected_role.lower()
        )
        items.append(
            ComparisonItem(
                field_name="target_role",
                pipeline1_value=plan.target_role,
                pipeline2_value=expected_role,
                is_match=role_matches,
                confidence_score=1.0 if role_matches else 0.0,
                notes="Role aligned with requirement matrix." if role_matches else "Role mismatch.",
            )
        )

        # 2. Check Required Topic Coverage
        required_topics = rule_data.get("required_topics", [])
        plan_titles = [m.title.lower() for m in plan.modules]
        for task in [t for m in plan.modules for t in m.tasks]:
            plan_titles.append(task.title.lower())

        for topic in required_topics:
            covered = any(topic.lower() in title for title in plan_titles)
            items.append(
                ComparisonItem(
                    field_name=f"topic_coverage[{topic}]",
                    pipeline1_value="Covered" if covered else "Missing",
                    pipeline2_value=f"Required: {topic}",
                    is_match=covered,
                    confidence_score=1.0 if covered else 0.0,
                    notes=f"Topic '{topic}' found in plan." if covered else f"Missing required topic '{topic}'.",
                )
            )

        # 3. Check Total Duration Time Budget
        max_minutes = rule_data.get("max_total_minutes", 480)
        total_minutes = sum(t.estimated_minutes for m in plan.modules for t in m.tasks)
        within_budget = total_minutes <= max_minutes
        items.append(
            ComparisonItem(
                field_name="total_duration_minutes",
                pipeline1_value=total_minutes,
                pipeline2_value=f"<= {max_minutes}",
                is_match=within_budget,
                confidence_score=1.0 if within_budget else 0.5,
                notes=f"Total {total_minutes}m within limit." if within_budget else f"Exceeds max {max_minutes}m.",
            )
        )

        # 4. Check Citations Completeness
        all_tasks = [t for m in plan.modules for t in m.tasks]
        tasks_with_quotes = sum(1 for t in all_tasks if t.source_citation.exact_quote.strip())
        citations_complete = (tasks_with_quotes == len(all_tasks)) if all_tasks else False
        items.append(
            ComparisonItem(
                field_name="citations_completeness",
                pipeline1_value=f"{tasks_with_quotes}/{len(all_tasks)} cited",
                pipeline2_value="100% cited",
                is_match=citations_complete,
                confidence_score=1.0 if citations_complete else 0.0,
                notes="All tasks carry exact citations." if citations_complete else "Some tasks lack citations.",
            )
        )

        # 5. Security Scan: Prompt Injection check
        security_threats: list[SecurityThreatFlag] = []
        for c in doc_chunks:
            matches = scan_for_prompt_injection(c.content)
            for m in matches:
                security_threats.append(
                    SecurityThreatFlag(
                        threat_id=f"THREAT-{uuid.uuid4().hex[:6].upper()}",
                        pattern_matched=m,
                        excerpt=c.content[:100],
                        severity="CRITICAL",
                    )
                )

        # 6. Run Hallucination & Contradiction checks
        from src.hallucination_checks.detector import detect_hallucinations
        hallucinations = detect_hallucinations(plan, doc_chunks)
        contradictions = check_contradictions(plan=plan, doc_chunks=doc_chunks)

        # Calculate scores
        total_checks = len(items)
        matched_checks = sum(1 for i in items if i.is_match)
        match_score = (matched_checks / total_checks) if total_checks > 0 else 0.0

        status, summary = classify_verification_status(
            match_score=match_score,
            hallucinations=hallucinations,
            contradictions=contradictions,
            security_threats=security_threats,
        )

        return ComparisonReport(
            report_id=f"REP-{uuid.uuid4().hex[:8].upper()}",
            doc_id=plan.source_citation.doc_id,
            target_role=plan.target_role,
            status=status,
            match_score=round(match_score, 3),
            total_checks=total_checks,
            matched_checks=matched_checks,
            items=items,
            hallucinations=hallucinations,
            contradictions=contradictions,
            security_threats=security_threats,
            summary=summary,
        )
