"""A stand-in for Gemini that reads the real prompt and answers from the chunks inside it.

It exercises prompt formatting, structured-output parsing and grounding without network calls.
Faults can be injected per document code to test the pipeline's defences.
"""
import re
import threading
from dataclasses import dataclass, field

from app.genai_pipeline.client import GenerationError, LLMResult
from app.genai_pipeline.schemas import LessonDraft, ModuleDraft, QuestionDraft, QuizDraft, TaskDraft
from app.genai_pipeline.text import split_sentences

_CHUNK = re.compile(r'<chunk id="([^"]+)" section="([^"]*)"(?: page="\d+")?>\n(.*?)\n</chunk>', re.S)
_DOC = re.compile(r'<document code="([^"]+)"')


@dataclass
class FakeLLM:
    model: str = "fake-gemini"
    fail_docs: set[str] = field(default_factory=set)            # raise GenerationError for these codes
    hallucinate_docs: set[str] = field(default_factory=set)     # quotes that are not in the document
    bad_quiz_docs: set[str] = field(default_factory=set)        # correct option missing from the quote
    no_criteria_docs: set[str] = field(default_factory=set)     # tasks without completion criteria
    invented_deadline_docs: set[str] = field(default_factory=set)  # criteria with a deadline the chunk never states
    untaught_docs: set[str] = field(default_factory=set)        # no lesson on the last chunk, but tasks/quiz on it
    calls: list[dict] = field(default_factory=list)
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def generate(self, *, system, prompt, schema, temperature):
        code = _DOC.search(prompt).group(1)
        chunks = [{"id": m.group(1), "section": m.group(2), "text": m.group(3)} for m in _CHUNK.finditer(prompt)]
        with self._lock:
            self.calls.append({"doc": code, "schema": schema.__name__, "system": system, "prompt": prompt})
        if code in self.fail_docs:
            raise GenerationError("UPSTREAM_UNAVAILABLE", "simulated outage")
        data = self._module(code, chunks) if schema is ModuleDraft else self._quiz(code, chunks)
        return LLMResult(data=data, model=self.model, input_tokens=len(prompt) // 4, output_tokens=100)

    def _module(self, code, chunks) -> ModuleDraft:
        lessons, tasks = [], []
        for i, c in enumerate(chunks):
            sentences = split_sentences(c["text"]) or [c["text"]]
            quote = "This rule was invented by the model." if code in self.hallucinate_docs else sentences[0]
            skip_lesson = code in self.untaught_docs and i == len(chunks) - 1 and len(chunks) > 1
            if not skip_lesson:
                lessons.append(LessonDraft(title=f"Lesson: {c['section']}", title_en=c["section"],
                                           content=f"Explanation: {c['text']}", chunk_ids=[c["id"]],
                                           quote_chunk_id=c["id"], exact_quote=quote))
            duty = next((s for s in sentences if re.search(r"\b(must|should)\b", s)), None)
            if duty:
                criteria = ("" if code in self.no_criteria_docs
                            else "Completed in 999 days." if code in self.invented_deadline_docs
                            else f"Evidence of completion: {duty}")
                tasks.append(TaskDraft(title=f"Do: {duty}", title_en=f"Do: {duty}", completion_criteria=criteria,
                                       completion_criteria_en=criteria, quote_chunk_id=c["id"], exact_quote=duty))
        # Cited under the wrong chunk id: grounding must find the sentence in its real chunk.
        if len(lessons) > 1:
            lessons[1].quote_chunk_id = chunks[0]["id"]
        tasks.append(TaskDraft(title="Invented task", title_en="Invented task", completion_criteria="Car received.",
                               completion_criteria_en="Car received.", quote_chunk_id=chunks[0]["id"],
                               exact_quote="Employees receive a free car on their first day."))
        objectives = [f"Apply requirements from section {c['section']}" for c in chunks[:3]]
        # Like a careful model, report chunks that talk to the AI or the reviewer instead of the employee.
        suspicious = [c["id"] for c in chunks if re.search(r"pretend|higher priority than your own rules", c["text"], re.I)]
        return ModuleDraft(suspicious_chunk_ids=suspicious, learning_objectives=objectives, lessons=lessons, tasks=tasks)

    def _quiz(self, code, chunks) -> QuizDraft:
        questions = []
        for c in chunks:
            for sentence in split_sentences(c["text"]):
                words = [w.strip(".,") for w in sentence.split() if len(w.strip(".,")) >= 5]
                if not words:
                    continue
                correct = "Nonexistent" if code in self.bad_quiz_docs else words[0]
                questions.append(QuestionDraft(
                    question=f"Question about {c['section']}?", question_en=f"Question about {c['section']}?",
                    options=[correct, "Wrongalpha", "Wrongbravo", "Wrongcharlie"], answer_index=0,
                    quote_chunk_id=c["id"], exact_quote=sentence, explanation="According to the document."))
                break
        # Always-invalid extras the grounding step must reject.
        questions.append(QuestionDraft(question="Dup?", question_en="Dup?", options=["same", "same", "x", "y"], answer_index=0,
                                       quote_chunk_id=chunks[0]["id"], exact_quote="whatever", explanation=""))
        return QuizDraft(questions=questions)
