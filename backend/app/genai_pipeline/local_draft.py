"""Rule-based draft generator (engine "local-draft"). Port of frontend `utils/pathGenerator.js`.

Nothing is invented: lessons are the document's own sections, tasks and questions are built from
real sentences, and every item cites its chunk. Used when no Gemini key is configured, and per module
when a Gemini call fails, so HR always gets a reviewable draft.
"""
import math
import re
from dataclasses import dataclass

from app.genai_pipeline.text import split_sentences, stable_hash
from app.genai_pipeline.types import QUIZ_PER_MODULE, TASKS_PER_MODULE, GenerationRequest, SourceDoc, doc_tier, stage_template

LESSON_MAX_CHARS = 2500
DAY30_MAX_MODULES = 3

# Sentences stating a duty make good practice tasks.
_OBLIGATION = re.compile(r"\b(must|should|shall|required|need to|ensure|never|always)\b", re.IGNORECASE)
# A standalone number (not part of DOC-10, v1.0, ISO-27001); ASCII \w to match JavaScript.
_NUMBER = re.compile(r"(?<![\w.#/-])(\d{1,4})(?![\w/.-]?\d)(?![\w/-])", re.ASCII)


class NoContentError(ValueError):
    """None of the sources has usable (extracted, unflagged) text."""


@dataclass
class _Module:
    id: str
    doc: SourceDoc
    tier: int
    lessons: list[dict]
    sentences: dict[str, list[str]]  # lesson id → sentences


def place_answer(correct: str, distractors: list[str], seed: str) -> tuple[list[str], int]:
    """Insert the correct option at a position derived from `seed`, so regenerating gives the same quiz."""
    pos = stable_hash(seed) % (len(distractors) + 1)
    options = list(distractors)
    options.insert(pos, correct)
    return options, pos


def _number_distractors(n: int) -> list[str]:
    candidates = [n * 2, n + (5 if n >= 10 else 1), n - (5 if n >= 10 else 1), math.floor(n / 2 + 0.5), n * 3, n + 2]
    unique = list(dict.fromkeys(x for x in candidates if x > 0 and x != n))
    return [str(x) for x in unique[:3]]


def make_cloze_question(sentence: str) -> dict | None:
    # A leading "1. " is list numbering, not knowledge.
    body = re.sub(r"^\d+[.)]\s+", "", sentence)
    offset = len(sentence) - len(body)
    m = _NUMBER.search(body)
    if not m:
        return None
    distractors = _number_distractors(int(m.group(1)))
    if len(distractors) < 3:
        return None
    start = offset + m.start(1)
    blanked = f"{sentence[:start]}_____{sentence[start + len(m.group(1)):]}"
    return {"blanked": blanked, "correct": m.group(1), "distractors": distractors}


def _group_sections(chunks: list[dict]) -> list[dict]:
    sections: list[dict] = []
    for c in chunks:
        if sections and sections[-1]["section_id"] == c["section_id"]:
            sections[-1]["chunks"].append(c)
        else:
            sections.append({"section_id": c["section_id"], "heading": c["heading"], "chunks": [c]})
    return sections


def assign_stage(purpose: str, tier: int, day30_count: int) -> str:
    if purpose == "promotion":
        return "foundation" if tier <= 2 else "deep" if tier == 3 else "practice"
    if tier == 0:
        return "day1"
    if tier == 1:
        return "week1"
    if tier == 2:
        return "week2"
    if tier == 3:
        return "day30" if day30_count < DAY30_MAX_MODULES else "day60"
    return "day60"


def usable_chunks(doc: SourceDoc) -> tuple[list[dict], list[dict]]:
    """Split a document's chunks into (kept, excluded) — chunks with injection flags never reach a path."""
    flagged: dict[str, list[str]] = {}
    for f in doc.flags:
        flagged.setdefault(f["chunk_id"], []).append(f["rule_id"])
    kept, excluded = [], []
    for c in doc.chunks:
        if c["chunk_id"] in flagged:
            excluded.append({"doc": doc.code, "doc_id": doc.id, "chunk_id": c["chunk_id"], "rule_ids": flagged[c["chunk_id"]]})
        else:
            kept.append(c)
    return kept, excluded


def order_docs(docs: list[SourceDoc]) -> list[SourceDoc]:
    return sorted(docs, key=lambda d: (doc_tier(d), d.code))


def source_reference(doc: SourceDoc, chunk: dict, quote: str, section: str | None = None) -> dict:
    # A section without a heading (document preamble) is named after the document, not "S001".
    return {"doc_id": doc.id, "doc": doc.code, "section": section or chunk["heading"] or doc.title_en or doc.title,
            "page": chunk["page"], "chunk_id": chunk["chunk_id"], "exact_quote": quote}


def module_shell(module_id: str, doc: SourceDoc) -> dict:
    return {"id": module_id, "kind": "lesson", "title": doc.title_en or doc.title, "titleEn": doc.title_en or doc.title,
            "doc_id": doc.id, "doc_code": doc.code, "tier": doc_tier(doc)}


def generate(req: GenerationRequest, docs: list[SourceDoc]) -> tuple[list[dict], list[dict]]:
    """Build every module with the rules engine.

    Returns:
        (modules in study order, excluded chunks). Stage placement is done by `arrange_stages`.

    Raises:
        NoContentError: no source has usable text.
    """
    excluded: list[dict] = []
    modules: list[_Module] = []
    for doc in order_docs(docs):
        chunks, dropped = usable_chunks(doc)
        excluded.extend(dropped)
        if not chunks:
            continue
        module_id = f"{req.path_id}-M{len(modules) + 1}"
        lessons, sentences = [], {}
        for i, section in enumerate(_group_sections(chunks), start=1):
            full = "\n\n".join(c["content"] for c in section["chunks"])
            lesson_sentences = split_sentences(full)
            lesson_id = f"{module_id}-L{i}"
            lessons.append({
                "id": lesson_id,
                "title": section["heading"] or "",
                "content": f"{full[:LESSON_MAX_CHARS]}…" if len(full) > LESSON_MAX_CHARS else full,
                "minutes": max(1, math.ceil(len(re.split(r"\s+", full)) / 180)),
                "source_reference": source_reference(doc, section["chunks"][0],
                                                     lesson_sentences[0] if lesson_sentences else full[:160].strip(),
                                                     section["heading"] or None),
            })
            sentences[lesson_id] = lesson_sentences
        modules.append(_Module(module_id, doc, doc_tier(doc), lessons, sentences))
    if not modules:
        raise NoContentError("No source document has usable text")

    all_sentences = [(s, lesson_id) for m in modules for lesson_id, ss in m.sentences.items() for s in ss]
    built = []
    for m in modules:
        built.append(module_shell(m.id, m.doc) | {
            "lessons": m.lessons,
            "tasks": _tasks(m, req.level),
            "quiz": _quiz(m, req.level, all_sentences),
        })
    return built, excluded


def _ref(lesson: dict, sentence: str) -> dict:
    return lesson["source_reference"] | {"exact_quote": sentence}


def _quiz(m: _Module, level: str, all_sentences: list[tuple[str, str]]) -> list[dict]:
    target = QUIZ_PER_MODULE.get(level, 4)
    quiz: list[dict] = []
    used: set[str] = set()
    code = m.doc.code

    # Round 1: a sentence with a figure becomes a fill-in-the-blank question on that figure.
    for lesson in m.lessons:
        for s in m.sentences[lesson["id"]]:
            if len(quiz) >= target:
                break
            cloze = make_cloze_question(s)
            if not cloze:
                continue
            options, answer = place_answer(cloze["correct"], cloze["distractors"], s)
            section = lesson["source_reference"]["section"]
            quiz.append({
                "id": f"{m.id}-Q{len(quiz) + 1}", "kind": "cloze",
                "question": f"Fill in the blank ({code} · {section}): “{cloze['blanked']}”",
                "questionEn": f"Fill in the blank ({code} · {section}): “{cloze['blanked']}”",
                "options": options, "answer": answer, "source_reference": _ref(lesson, s),
            })
            used.add(s)
            break

    # Round 2: pick the true statement of a section; distractors are real sentences from elsewhere.
    for lesson in m.lessons:
        if len(quiz) >= target:
            break
        s = next((x for x in m.sentences[lesson["id"]] if x not in used), None)
        if s is None:
            continue
        others = [x for x, lesson_id in all_sentences if lesson_id != lesson["id"] and x != s]
        if len(others) < 3:
            continue
        step = max(1, len(others) // 3)
        start = stable_hash(s) % len(others)
        distractors = [others[(start + k * step) % len(others)] for k in range(3)]
        if len(set(distractors)) < 3:
            continue
        options, answer = place_answer(s, distractors, s)
        section = lesson["source_reference"]["section"]
        quiz.append({
            "id": f"{m.id}-Q{len(quiz) + 1}", "kind": "statement",
            "question": f"According to {code} · “{section}”, which statement is correct?",
            "questionEn": f"According to {code} · “{section}”, which statement is correct?",
            "options": options, "answer": answer, "source_reference": _ref(lesson, s),
        })
        used.add(s)
    return quiz


def completion_criteria(code: str, section: str) -> tuple[str, str]:
    """Criteria for a task built from a quoted obligation. The rules cannot know the evidence a policy expects,
    so the criterion points back at the quoted rule instead of inventing a deliverable."""
    return (f"Carried out the quoted requirement ({code} · {section}) correctly at least once in real work.",
            f"Carried out the quoted requirement ({code} · {section}) correctly at least once in real work.")


def _tasks(m: _Module, level: str) -> list[dict]:
    target = TASKS_PER_MODULE.get(level, 2)
    tasks: list[dict] = []
    for lesson in m.lessons:
        for s in m.sentences[lesson["id"]]:
            if len(tasks) >= target:
                break
            if _OBLIGATION.search(s) and not any(t["title"] == s for t in tasks):
                criteria, criteria_en = completion_criteria(m.doc.code, lesson["source_reference"]["section"])
                tasks.append({"id": f"{m.id}-T{len(tasks) + 1}", "title": s, "completion_criteria": criteria,
                              "completion_criteriaEn": criteria_en, "source_reference": _ref(lesson, s)})
    return tasks


def plan_stages(req: GenerationRequest, modules: list[dict]) -> dict[str, str]:
    """Module id → stage key. Milestones past the chosen duration fold into its last stage, so a one-week path
    still teaches every source, just earlier."""
    template = stage_template(req.purpose, req.duration_days)
    plan: dict[str, str] = {}
    day30 = 0
    for m in modules:
        key = assign_stage(req.purpose, m["tier"], day30)
        if key == "day30":
            day30 += 1
        plan[m["id"]] = key if key in template else template[-1]
    return plan


def arrange_stages(req: GenerationRequest, modules: list[dict]) -> list[dict]:
    """Place modules on the stage template and append the final assessment to the last stage.

    The assessment takes the first question of every module, so it covers each source once.
    """
    template = stage_template(req.purpose, req.duration_days)
    stage_map: dict[str, list[dict]] = {k: [] for k in template}
    plan = plan_stages(req, modules)
    for m in modules:
        stage_map[plan[m["id"]]].append(m)

    final_quiz = [m["quiz"][0] | {"id": f"{req.path_id}-FA-Q{i}"}
                  for i, m in enumerate((m for m in modules if m["quiz"]), start=1)]
    if final_quiz:
        stage_map[template[-1]].append({
            "id": f"{req.path_id}-FA", "kind": "assessment", "title": "Final Assessment", "titleEn": "Final Assessment",
            "doc_id": None, "doc_code": None, "tier": 5, "lessons": [], "tasks": [], "quiz": final_quiz,
        })
    return [{"key": k, "modules": stage_map[k]} for k in template if stage_map[k]]
