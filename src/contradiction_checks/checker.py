import re
from src.document_processing.chunker import DocumentChunk
from src.genai_pipeline.response_schemas import OnboardingPlanSchema
from src.schemas.comparison_contract import ContradictionFlag

CONTRADICTION_TOPICS = {
    "password_expiry": {
        "pattern": re.compile(r"passwords?\s+.*?(?:changed|expire|valid)\s+(?:every\s+)?(\d+)\s*(days?|months?)", re.I),
        "topic": "Password Expiry Interval",
    },
    "notice_period": {
        "pattern": re.compile(r"(\d+)\s*(days?|weeks?|months?)\s+(?:written\s+)?notice", re.I),
        "topic": "Resignation / Termination Notice Period",
    },
    "annual_leave": {
        "pattern": re.compile(r"(\d+)\s*(?:working\s+)?days?\s+(?:of\s+)?annual\s+leave", re.I),
        "topic": "Annual Leave Allowance",
    },
    "probation_period": {
        "pattern": re.compile(r"(\d+)\s*(months?|days?|weeks?)\s+probation", re.I),
        "topic": "Probation Period",
    },
}


def check_contradictions(
    plan: OnboardingPlanSchema | None = None,
    doc_chunks: list[DocumentChunk] | None = None,
) -> list[ContradictionFlag]:
    """Find conflicting policy rules or contradictory numbers within plan and chunks."""
    flags: list[ContradictionFlag] = []

    text_sources = []
    if doc_chunks:
        for c in doc_chunks:
            text_sources.append((f"Chunk {c.chunk_id} (Page {c.page_number})", c.content))

    if plan:
        for mod in plan.modules:
            for task in mod.tasks:
                text_sources.append((f"Task {task.task_id}", f"{task.title}. {task.description}"))

    for topic_key, config in CONTRADICTION_TOPICS.items():
        pattern = config["pattern"]
        topic_name = config["topic"]
        found_values = {}

        for source_name, text in text_sources:
            for match in pattern.finditer(text):
                matched_val = " ".join(match.groups()).strip().lower()
                full_sentence = match.group(0).strip()
                if matched_val not in found_values:
                    found_values[matched_val] = (source_name, full_sentence)

        # If more than 1 distinct value is stated for the same topic -> contradiction
        if len(found_values) > 1:
            items = list(found_values.items())
            val_a, (src_a, stmt_a) = items[0]
            val_b, (src_b, stmt_b) = items[1]
            flags.append(
                ContradictionFlag(
                    conflict_id=f"CONF-{topic_key.upper()}",
                    topic=topic_name,
                    statement_a=f"[{src_a}] {stmt_a}",
                    statement_b=f"[{src_b}] {stmt_b}",
                    source_reference=f"{src_a} vs {src_b}",
                    severity="HIGH",
                )
            )

    return flags
