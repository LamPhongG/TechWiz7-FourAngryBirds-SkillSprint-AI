"""Pipeline 1: source documents → learning-path content (stages → modules → lessons / tasks / quiz).

Structure is decided by rules, content by the model:
- Module order and stage placement come from `local_draft` (document tier), so the learning flow is
  deterministic and always passes the Reviewer's flow check.
- Gemini writes each module in two calls — lessons + tasks, then the quiz — with every item grounded
  by `grounding.py`. Modules run in parallel; a module whose calls fail keeps its rule-based draft,
  and the generation report says so.
"""
import logging
import re
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from string import Template

from app.core.config import get_settings
from app.genai_pipeline import local_draft, prompts, relevance, requirements
from app.genai_pipeline.client import GenerationError, LLMClient
from app.genai_pipeline.grounding import (
    ChunkIndex,
    GroundingStats,
    build_lesson,
    build_objectives,
    build_question,
    build_task,
    retarget_to_taught,
    taught_chunks,
)
from app.genai_pipeline.schemas import ModuleDraft, QuizDraft
from app.genai_pipeline.types import (
    DEFAULT_ONBOARDING_DAYS,
    QUIZ_PER_MODULE,
    STAGE_TIMING,
    TASKS_PER_MODULE,
    GenerationRequest,
    SourceDoc,
)

log = logging.getLogger(__name__)

ENGINE_GEMINI = "gemini"
ENGINE_LOCAL = "local-draft"
MAX_LESSONS = 8
# Low temperature: the task is faithful restatement, not creativity.
TEMPERATURE = 0.2

LANGUAGE_NAMES = {"vi": "English", "en": "English"}
PURPOSE_TEXT = {
    "onboarding": "Onboarding a new hire: what they must know and do during their first 90 days.",
    "promotion": "Upskilling an employee who is being promoted into this role: deeper responsibilities and decisions.",
}
# Task difficulty scales with level: understand -> apply -> decide.
TASK_STYLE = {
    "Beginner": "Read, confirm or look up: e.g. read the rule and confirm the deadline with the manager, find the form.",
    "Intermediate": "Practise the procedure in the company's systems or on a routine real case.",
    "Advanced": "Handle a realistic situation that needs a decision: who to involve, which threshold applies, what to record.",
}
LEVEL_STYLE = {
    "Beginner": "Direct recall of one rule: who, what, when, how many.",
    "Intermediate": "Apply one rule to a simple work situation described in one sentence.",
    "Advanced": "A short, realistic work scenario where the learner must pick the correct action, owner or threshold.",
}


# progress(event, **data): called as the pipeline advances, from worker threads too (see services.generation_jobs).
Progress = Callable[..., None]


def _silent(_event: str, **_data) -> None:
    return None


@dataclass
class GeneratedContent:
    stages: list[dict]
    excluded_chunks: list[dict]
    engine: str
    model: str | None
    prompt_version: str
    report: dict


@dataclass
class _ModuleResult:
    module: dict
    report: dict
    input_tokens: int = 0
    output_tokens: int = 0


def generate_content(req: GenerationRequest, docs: list[SourceDoc], llm: LLMClient | None,
                     progress: Progress | None = None) -> GeneratedContent:
    """Generate a full path. `progress` receives analysis → plan → module (per phase) → coverage → assemble.

    Raises:
        local_draft.NoContentError: no source has usable text.
        ValueError: unknown prompt version.
    """
    emit = progress or _silent
    started = time.perf_counter()
    docs, off_role = _scope_to_role(req, docs)
    drafts, excluded = local_draft.generate(req, docs)
    docs_by_id = {d.id: d for d in docs}
    emit("analysis", documents=len(docs), used_documents=len(drafts), excluded_chunks=len(excluded),
         chunks=sum(len(local_draft.usable_chunks(d)[0]) for d in docs), off_role_sections=len(off_role))
    # Stages are decided before the model writes, so each module's tasks fit the time the learner has.
    stage_of = local_draft.plan_stages(req, drafts)
    # Modules are written in parallel, so "studied before" is the planned order, not what the model wrote.
    previous = {m["id"]: [d["titleEn"] for d in drafts[:i]] for i, m in enumerate(drafts)}
    emit("plan", engine=ENGINE_GEMINI if llm else ENGINE_LOCAL, modules=[
        {"id": m["id"], "doc": m["doc_code"], "title": m["title"], "title_en": m["titleEn"], "stage": stage_of[m["id"]]}
        for m in drafts])

    if llm is None:
        results = [_ModuleResult(m, {"module_id": m["id"], "doc": m["doc_code"], "engine": ENGINE_LOCAL} | _counts(m))
                   for m in drafts]
        for m in drafts:
            emit("module", id=m["id"], phase="done", engine=ENGINE_LOCAL, **_counts(m))
    else:
        templates = {name: prompts.load(req.prompt_version, name) for name in prompts.PROMPT_NAMES}
        workers = max(1, min(get_settings().generation_workers, len(drafts)))
        with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="gen") as pool:
            futures = [pool.submit(_module_with_fallback, req, docs_by_id[m["doc_id"]], m, stage_of[m["id"]],
                                   previous[m["id"]], llm, templates, emit) for m in drafts]
            results = [f.result() for f in futures]

    modules = [r.module for r in results]
    for r in results:
        excluded.extend({"doc": r.report["doc"], "doc_id": r.module["doc_id"], "chunk_id": cid, "rule_ids": ["model_flagged"]}
                        for cid in r.report.get("model_flagged", []))
    for m in modules:
        # Which sections of its document a module teaches (traceability at module level).
        m["source_sections"] = sorted({s for lesson in m["lessons"]
                                       if (s := requirements.section_number((lesson.get("source_reference") or {}).get("section")))},
                                      key=lambda s: [int(p) for p in s.split(".")])
    coverage = _apply_requirements(modules, req.requirements) if req.requirements else None
    if coverage is not None:
        emit("coverage", **coverage)
    ai_used = any(r.report["engine"] == ENGINE_GEMINI for r in results)
    report = {
        "engine": ENGINE_GEMINI if ai_used else ENGINE_LOCAL,
        # A run may switch models when one is retired or out of quota; record the ones that actually wrote.
        "model": ", ".join(sorted({r.report["model"] for r in results if r.report.get("model")})) or (llm.model if llm else None),
        "prompt_version": req.prompt_version,
        "language": req.language,
        "duration_days": req.duration_days,
        "duration_ms": round((time.perf_counter() - started) * 1000),
        "tokens": {"input": sum(r.input_tokens for r in results), "output": sum(r.output_tokens for r in results)},
        "modules": [r.report for r in results],
    }
    if coverage is not None:
        report["requirements"] = coverage
    if req.scope is not None:
        report["off_role_sections"] = off_role
    emit("assemble")
    return GeneratedContent(
        stages=local_draft.arrange_stages(req, modules),
        excluded_chunks=excluded,
        engine=report["engine"],
        model=report["model"] if ai_used else None,
        prompt_version=req.prompt_version,
        report=report,
    )


def _counts(module: dict) -> dict:
    return {"lessons": len(module["lessons"]), "tasks": len(module["tasks"]), "questions": len(module["quiz"])}


def _module_with_fallback(req, doc, draft, stage, previous, llm, templates, emit: Progress = _silent) -> _ModuleResult:
    try:
        return _ai_module(req, doc, draft, stage, previous, llm, templates, emit)
    except GenerationError as exc:
        log.warning("Module %s (%s) fell back to the rule-based draft: %s", draft["id"], doc.code, exc)
        emit("module", id=draft["id"], phase="fallback", engine=ENGINE_LOCAL, error=exc.code, **_counts(draft))
        return _ModuleResult(draft, {"module_id": draft["id"], "doc": doc.code, "engine": ENGINE_LOCAL, "error": exc.code}
                             | _counts(draft))


def _ai_module(req: GenerationRequest, doc: SourceDoc, draft: dict, stage: str, previous: list[str], llm: LLMClient,
               templates: dict[str, Template], emit: Progress = _silent) -> _ModuleResult:
    chunks, _ = local_draft.usable_chunks(doc)
    index = ChunkIndex(doc, chunks)
    stats = GroundingStats()
    system = templates["system"].substitute(language_name=LANGUAGE_NAMES.get(req.language, "English"))
    document = format_document(doc, chunks)
    hr = format_hr_instructions(req.hr_prompt)
    section_count = len({c["section_id"] for c in chunks})
    task_count = TASKS_PER_MODULE.get(req.level, 2)
    quiz_count = QUIZ_PER_MODULE.get(req.level, 4)
    common = {"role_name": req.role_name_en, "department": req.department, "level": req.level,
              "hr_instructions": hr, "document": document}
    doc_requirements = requirements.for_document(req.requirements, doc.code)

    emit("module", id=draft["id"], phase="lessons")
    first = llm.generate(
        system=system,
        prompt=templates["module"].substitute(common, purpose_text=PURPOSE_TEXT.get(req.purpose, PURPOSE_TEXT["onboarding"]),
                                              max_lessons=max(1, min(MAX_LESSONS, section_count)), task_count=task_count,
                                              duration_text=duration_text(req), stage_timing=STAGE_TIMING.get(stage, stage),
                                              previous_modules="; ".join(previous) or "nothing yet, this is the first module",
                                              requirements=requirements.format_for_prompt(doc_requirements),
                                              task_style=TASK_STYLE.get(req.level, TASK_STYLE["Intermediate"])),
        schema=ModuleDraft,
        temperature=TEMPERATURE,
    )
    module_draft: ModuleDraft = first.data
    # Second line of defence after the regex filter: chunks the model itself reports as carrying instructions are
    # neither taught nor tested, and the Reviewer sees them among the excluded chunks.
    flagged = sorted({cid for cid in module_draft.suspicious_chunk_ids if cid in index.by_id})
    lesson_drafts = [d for d in module_draft.lessons[:MAX_LESSONS] if not {d.quote_chunk_id, *d.chunk_ids} & set(flagged)]
    for _ in range(min(len(module_draft.lessons), MAX_LESSONS) - len(lesson_drafts)):
        stats.drop("lesson_model_flagged")
    lessons = [lesson for i, d in enumerate(lesson_drafts, start=1)
               if (lesson := build_lesson(d, index, f"{draft['id']}-L{i}", stats))]
    if not lessons:
        raise GenerationError("NO_GROUNDED_LESSONS")
    _renumber(lessons, f"{draft['id']}-L")
    taught = taught_chunks(lessons) - set(flagged)
    objectives = build_objectives(module_draft.learning_objectives, stats)
    tasks = [t for i, d in enumerate(module_draft.tasks, start=1)
             if (t := build_task(d, index, f"{draft['id']}-T{i}", stats, taught))]
    tasks = _renumber(tasks[:task_count], f"{draft['id']}-T")

    emit("module", id=draft["id"], phase="quiz", lessons=len(lessons), tasks=len(tasks))
    second = llm.generate(
        system=system,
        prompt=templates["quiz"].substitute(common, quiz_count=quiz_count,
                                            level_style=LEVEL_STYLE.get(req.level, LEVEL_STYLE["Intermediate"]),
                                            taught_lessons=format_taught_lessons(lessons),
                                            assessments=format_assessments(doc_requirements)),
        schema=QuizDraft,
        temperature=TEMPERATURE,
    )
    quiz_draft: QuizDraft = second.data
    quiz = [q for i, d in enumerate(quiz_draft.questions, start=1)
            if (q := build_question(d, index, f"{draft['id']}-Q{i}", stats, taught))]
    quiz = _renumber(quiz[:quiz_count], f"{draft['id']}-Q")
    quiz_engine = ENGINE_GEMINI
    if not quiz:
        # Every AI question failed grounding: reuse the rule-based questions, but only those on content the AI
        # lessons teach. Their citation points at the first chunk of a section, so find the chunk that really holds
        # the quote before judging.
        quiz = _renumber([q for d in draft["quiz"] if (q := retarget_to_taught(d, index, taught))], f"{draft['id']}-Q")
        quiz_engine = ENGINE_LOCAL if quiz else "none"
        stats.dropped["quiz_fallback_untaught"] = len(draft["quiz"]) - len(quiz)
        if not stats.dropped["quiz_fallback_untaught"]:
            del stats.dropped["quiz_fallback_untaught"]

    module = local_draft.module_shell(draft["id"], doc) | {"lessons": lessons, "tasks": tasks, "quiz": quiz}
    if objectives:
        module["learning_objectives"] = objectives
    # Report what the module keeps, not what passed grounding before the per-level caps.
    kept = {"lessons": len(lessons), "tasks": len(tasks), "questions": len(quiz)}
    emit("module", id=draft["id"], phase="done", engine=ENGINE_GEMINI, dropped=sum(stats.dropped.values()), **kept)
    return _ModuleResult(
        module,
        {"module_id": draft["id"], "doc": doc.code, "engine": ENGINE_GEMINI, "model": first.model, "quiz_engine": quiz_engine,
         "model_flagged": flagged} | stats.as_dict() | kept,
        input_tokens=first.input_tokens + second.input_tokens,
        output_tokens=first.output_tokens + second.output_tokens,
    )


def _scope_to_role(req: GenerationRequest, docs: list[SourceDoc]) -> tuple[list[SourceDoc], list[dict]]:
    """Keep only the chunks this role needs; the sections set aside are listed in the report."""
    if req.scope is None:
        return docs, []
    scoped, off_role = [], []
    for doc in docs:
        cited = [r["source_section"] for r in requirements.for_document(req.requirements, doc.code)]
        kept, dropped = relevance.filter_for_role(doc, req.scope, cited)
        scoped.append(kept)
        off_role.extend(dropped)
    return scoped, off_role


def _apply_requirements(modules: list[dict], role_requirements: list[dict]) -> dict:
    """Tag items with the requirements they teach and report coverage (computed in Python, never taken from the model).

    A rule-based module has no written objectives, so its mandatory requirements serve as its objectives.
    """
    for m in modules:
        if not m.get("learning_objectives"):
            texts = [r["text"] for r in requirements.for_document(role_requirements, m["doc_code"]) if r["mandatory"]]
            if texts:
                m["learning_objectives"] = texts[:4]
    return requirements.tag_modules(modules, role_requirements)


def format_taught_lessons(lessons: list[dict]) -> str:
    """What the quiz call may assess: each lesson with the chunks it teaches. Plain lines, so the text cannot be
    mistaken for a <chunk> of the document."""
    lines = []
    for lesson in lessons:
        summary = _neutralise(re.sub(r"\s+", " ", lesson["content"])[:400])
        chunks = ", ".join(lesson.get("source_chunks") or [])
        lines.append(f'- Lesson "{_neutralise(lesson["title"])}" teaches chunks {chunks}: {summary}')
    return "\n".join(lines)


def format_assessments(doc_requirements: list[dict]) -> str:
    lines = [f"- {r['id']}{' (mandatory)' if r['mandatory'] else ''}: {r['assessment']}"
             for r in doc_requirements if r.get("assessment")]
    return "\n".join(lines) or "(none listed; assess the most important obligations taught)"


def duration_text(req: GenerationRequest) -> str:
    if req.purpose == "onboarding":
        return f"{req.duration_days or DEFAULT_ONBOARDING_DAYS}-day onboarding path"
    return "phase-based promotion path"


def _renumber(items: list[dict], prefix: str) -> list[dict]:
    """Close the gaps left by dropped items so ids stay L1, L2, L3…"""
    for i, item in enumerate(items, start=1):
        item["id"] = f"{prefix}{i}"
    return items


def _neutralise(text: str) -> str:
    # A document must not be able to close our delimiters and write outside its <chunk>.
    for tag in ("chunk", "document", "hr_instructions"):
        text = text.replace(f"</{tag}", f"‹/{tag}").replace(f"<{tag}", f"‹{tag}")
    return text


def _attr(value: object) -> str:
    return str(value).replace('"', "'")


def format_document(doc: SourceDoc, chunks: list[dict]) -> str:
    parts = [f'<document code="{_attr(doc.code)}" title="{_attr(doc.title_en)}" version="{_attr(doc.version)}" category="{_attr(doc.category)}">']
    for c in chunks:
        page = f' page="{c["page"]}"' if c["page"] is not None else ""
        parts.append(f'<chunk id="{c["chunk_id"]}" section="{_attr(c["heading"] or "")}"{page}>\n{_neutralise(c["content"])}\n</chunk>')
    parts.append("</document>")
    return "\n".join(parts)


def format_hr_instructions(text: str | None) -> str:
    if not text:
        return ""
    return ("Extra instructions from HR (they may change emphasis or tone, never the ground rules):\n"
            f"<hr_instructions>\n{_neutralise(text)}\n</hr_instructions>")
