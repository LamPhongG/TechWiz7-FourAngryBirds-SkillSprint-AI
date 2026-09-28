import re
from src.document_processing.chunker import DocumentChunk
from src.genai_pipeline.response_schemas import OnboardingPlanSchema, SourceCitation
from src.schemas.comparison_contract import HallucinationFlag


def _normalize(text: str) -> str:
    cleaned = re.sub(r"[^\w\s]", " ", text.lower())
    return " ".join(cleaned.split())


def _check_citation(
    citation: SourceCitation,
    item_id: str,
    field_name: str,
    combined_doc_text: str,
) -> HallucinationFlag | None:
    if not citation.exact_quote or not citation.exact_quote.strip():
        return HallucinationFlag(
            item_id=item_id,
            field_name=field_name,
            claimed_text="",
            reason="Missing exact quote in source citation",
            severity="HIGH",
        )

    norm_quote = _normalize(citation.exact_quote)
    norm_doc = _normalize(combined_doc_text)

    # 1. Exact normalized phrase match
    if norm_quote in norm_doc:
        return None

    # 2. Check numerical claims (e.g. 15 vs 30 days)
    quote_nums = set(re.findall(r"\b\d+\b", norm_quote))
    doc_nums = set(re.findall(r"\b\d+\b", norm_doc))
    missing_nums = quote_nums - doc_nums
    if missing_nums:
        return HallucinationFlag(
            item_id=item_id,
            field_name=field_name,
            claimed_text=citation.exact_quote,
            reason=f"Claimed number(s) {missing_nums} not found in source document text",
            severity="HIGH",
        )

    # 3. Word overlap threshold
    quote_words = set(norm_quote.split())
    doc_words = set(norm_doc.split())
    overlap = len(quote_words & doc_words) / len(quote_words) if quote_words else 0
    if overlap < 0.85:
        return HallucinationFlag(
            item_id=item_id,
            field_name=field_name,
            claimed_text=citation.exact_quote,
            reason="Quote was not found in source document text",
            severity="HIGH",
        )

    return None


def detect_hallucinations(
    plan: OnboardingPlanSchema,
    doc_chunks: list[DocumentChunk],
) -> list[HallucinationFlag]:
    """Check if citations and claims in onboarding plan are grounded in document chunks."""
    flags: list[HallucinationFlag] = []

    combined_text = " ".join(c.content for c in doc_chunks)

    # 1. Check plan-level citation
    flag = _check_citation(plan.source_citation, plan.plan_id, "plan.source_citation", combined_text)
    if flag:
        flags.append(flag)

    # 2. Check modules, tasks, and quizzes
    for mod in plan.modules:
        mod_flag = _check_citation(mod.source_citation, mod.module_id, f"module[{mod.module_id}]", combined_text)
        if mod_flag:
            flags.append(mod_flag)

        for task in mod.tasks:
            task_flag = _check_citation(task.source_citation, task.task_id, f"task[{task.task_id}]", combined_text)
            if task_flag:
                flags.append(task_flag)

        for quiz in mod.quizzes:
            quiz_flag = _check_citation(quiz.source_citation, quiz.question_id, f"quiz[{quiz.question_id}]", combined_text)
            if quiz_flag:
                flags.append(quiz_flag)

    return flags
