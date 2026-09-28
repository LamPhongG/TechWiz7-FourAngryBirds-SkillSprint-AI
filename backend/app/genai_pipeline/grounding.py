"""Turn raw Gemini drafts into path items only when they can be traced back to the source.

The Reviewer's knowledge check (frontend `utils/pathChecks.js`) marks an item as a hallucination
when its quote is not in the document, and a quiz question as a contradiction when the correct option
is not inside its quote. Applying the same rules here means the model's mistakes are dropped (or the
citation repaired) before a human ever sees them. Citation metadata (doc id, section, page) is always
taken from the database, never from the model.
"""
import math
import re
from dataclasses import dataclass, field

from app.core.injection_filter import scan_chunks
from app.genai_pipeline.local_draft import place_answer, source_reference
from app.genai_pipeline.schemas import LessonDraft, QuestionDraft, TaskDraft
from app.genai_pipeline.text import normalize_for_match, split_sentences
from app.genai_pipeline.types import SourceDoc

MIN_QUOTE_CHARS = 15
MAX_QUOTE_CHARS = 300
MAX_OBJECTIVES = 4
_NUMBER = re.compile(r"\d+(?:[.,]\d+)*")


@dataclass
class GroundingStats:
    lessons: int = 0
    tasks: int = 0
    questions: int = 0
    repaired_quotes: int = 0
    dropped: dict[str, int] = field(default_factory=dict)

    def drop(self, reason: str) -> None:
        self.dropped[reason] = self.dropped.get(reason, 0) + 1

    def as_dict(self) -> dict:
        return {"lessons": self.lessons, "tasks": self.tasks, "questions": self.questions,
                "repaired_quotes": self.repaired_quotes, "dropped": dict(self.dropped)}


class ChunkIndex:
    """Chunks of one document with pre-normalised text for quote lookup."""

    def __init__(self, doc: SourceDoc, chunks: list[dict]):
        self.doc = doc
        self.chunks = chunks
        self.by_id = {c["chunk_id"]: c for c in chunks}
        self._norm = {c["chunk_id"]: normalize_for_match(c["content"]) for c in chunks}

    def locate(self, quote: str, preferred_id: str | None) -> dict | None:
        """Chunk containing `quote` verbatim (after normalisation), trying the chunk the model named first.

        Models often cite the right sentence under the wrong chunk id; searching the whole document
        keeps those citations instead of dropping good content.
        """
        needle = normalize_for_match(quote)
        if not MIN_QUOTE_CHARS <= len(needle) <= MAX_QUOTE_CHARS:
            return None
        if preferred_id in self._norm and needle in self._norm[preferred_id]:
            return self.by_id[preferred_id]
        return next((self.by_id[cid] for cid, text in self._norm.items() if needle in text), None)


def _has_injection(*texts: str) -> bool:
    return bool(scan_chunks([{"chunk_id": "out", "page": None, "content": "\n".join(texts)}]))


def build_lesson(draft: LessonDraft, index: ChunkIndex, lesson_id: str, stats: GroundingStats) -> dict | None:
    content = draft.content.strip()
    if not content:
        stats.drop("lesson_empty")
        return None
    # Model output is shown to employees, so it gets the same screening as the documents.
    if _has_injection(draft.title, content):
        stats.drop("lesson_injection")
        return None
    cited = [cid for cid in dict.fromkeys(draft.chunk_ids) if cid in index.by_id]
    quote = draft.exact_quote.strip()
    chunk = index.locate(quote, draft.quote_chunk_id)
    if chunk is None:
        # The explanation may still be right; cite a real sentence from the chunk the lesson is built on
        # instead of discarding it. The Reviewer sees the repaired count in the generation report.
        anchor = index.by_id.get(cited[0]) if cited else None
        if anchor is None:
            stats.drop("lesson_unsourced")
            return None
        sentences = split_sentences(anchor["content"])
        quote = sentences[0] if sentences else anchor["content"][:160].strip()
        chunk = anchor
        stats.repaired_quotes += 1
    if chunk["chunk_id"] not in cited:
        cited.insert(0, chunk["chunk_id"])
    stats.lessons += 1
    return {
        "id": lesson_id,
        "title": draft.title.strip() or chunk["heading"] or index.doc.title,
        "titleEn": draft.title_en.strip() or None,
        "content": content,
        "minutes": max(1, math.ceil(len(content.split()) / 180)),
        "source_chunks": cited,
        "source_reference": source_reference(index.doc, chunk, quote),
    }


def _numbers(text: str) -> set[str]:
    # "5,000,000" and "5.000.000" are the same amount, and "17:00" yields 17 and 00 on both sides.
    return {re.sub(r"[.,]", "", n) for n in _NUMBER.findall(text)}


def taught_chunks(lessons: list[dict]) -> set[str]:
    """Chunks the module's lessons teach: a task or question may only be about these (teach before you test)."""
    return {cid for lesson in lessons
            for cid in [*(lesson.get("source_chunks") or []), (lesson.get("source_reference") or {}).get("chunk_id")] if cid}


def retarget_to_taught(question: dict, index: ChunkIndex, taught: set[str]) -> dict | None:
    """A rule-based question kept only when its quote lies in a chunk the module's lessons teach, cited there."""
    ref = question.get("source_reference") or {}
    chunk = index.locate(ref.get("exact_quote") or "", ref.get("chunk_id"))
    if chunk is None or chunk["chunk_id"] not in taught:
        return None
    return question | {"source_reference": source_reference(index.doc, chunk, ref["exact_quote"], ref.get("section"))}


def build_objectives(objectives: list[str], stats: GroundingStats) -> list[str]:
    kept = []
    for text in objectives:
        text = re.sub(r"\s+", " ", text).strip()
        if not text:
            continue
        # Objectives are shown to employees like any other generated text.
        if _has_injection(text):
            stats.drop("objective_injection")
            continue
        if text not in kept:
            kept.append(text)
    return kept[:MAX_OBJECTIVES]


def build_task(draft: TaskDraft, index: ChunkIndex, task_id: str, stats: GroundingStats,
               taught: set[str] | None = None) -> dict | None:
    """A task needs a quoted source and completion criteria; Python validation rejects a task without either.

    `taught`: chunk ids the module's lessons cover; a task on any other chunk would test untaught content.
    """
    title = draft.title.strip()
    criteria = draft.completion_criteria.strip()
    chunk = index.locate(draft.exact_quote, draft.quote_chunk_id)
    if not title:
        stats.drop("task_empty")
        return None
    if chunk is None:
        stats.drop("task_quote_not_found")
        return None
    if taught is not None and chunk["chunk_id"] not in taught:
        stats.drop("task_untaught")
        return None
    if not criteria:
        stats.drop("task_no_criteria")
        return None
    # A deadline or amount the chunk never states is the most harmful thing a criterion can invent.
    if not _numbers(criteria) <= _numbers(chunk["content"]):
        stats.drop("task_criteria_unsupported")
        return None
    if _has_injection(title, criteria, draft.completion_criteria_en):
        stats.drop("task_injection")
        return None
    stats.tasks += 1
    return {"id": task_id, "title": title, "titleEn": draft.title_en.strip() or None,
            "completion_criteria": criteria, "completion_criteriaEn": draft.completion_criteria_en.strip() or None,
            "source_reference": source_reference(index.doc, chunk, draft.exact_quote.strip())}


def build_question(draft: QuestionDraft, index: ChunkIndex, question_id: str, stats: GroundingStats,
                   taught: set[str] | None = None) -> dict | None:
    options = [re.sub(r"\s+", " ", o).strip() for o in draft.options]
    if not draft.question.strip() or len(options) < 3 or not all(options):
        stats.drop("quiz_malformed")
        return None
    if len({normalize_for_match(o) for o in options}) != len(options):
        stats.drop("quiz_duplicate_options")
        return None
    if not 0 <= draft.answer_index < len(options):
        stats.drop("quiz_answer_out_of_range")
        return None
    chunk = index.locate(draft.exact_quote, draft.quote_chunk_id)
    if chunk is None:
        stats.drop("quiz_quote_not_found")
        return None
    if taught is not None and chunk["chunk_id"] not in taught:
        stats.drop("quiz_untaught")
        return None
    quote_norm = normalize_for_match(draft.exact_quote)
    correct = options[draft.answer_index]
    if normalize_for_match(correct) not in quote_norm:
        stats.drop("quiz_answer_not_in_quote")
        return None
    distractors = [o for i, o in enumerate(options) if i != draft.answer_index]
    # A wrong option that the quote also contains makes the question ambiguous.
    if any(normalize_for_match(d) in quote_norm for d in distractors):
        stats.drop("quiz_ambiguous")
        return None
    if _has_injection(draft.question, draft.question_en, *options):
        stats.drop("quiz_injection")
        return None
    # Models favour the first positions for the right answer; reposition it deterministically.
    shuffled, answer = place_answer(correct, distractors, draft.exact_quote)
    stats.questions += 1
    return {
        "id": question_id,
        "kind": "ai",
        "question": draft.question.strip(),
        "questionEn": draft.question_en.strip() or draft.question.strip(),
        "options": shuffled,
        "answer": answer,
        "explanation": draft.explanation.strip() or None,
        "source_reference": source_reference(index.doc, chunk, draft.exact_quote.strip()),
    }
