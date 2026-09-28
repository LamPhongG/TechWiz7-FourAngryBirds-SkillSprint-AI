"""Learning-path content tree, requests and responses.

Content items allow extra fields (`titleEn`, `questionEn`…) so nothing the generator adds is dropped,
while the fields the workflow and progress tracking rely on are validated.
"""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models import FinalStatus, PathLevel, PathPurpose, PathStatus, UserRole

MIN_REASON_LENGTH = 10  # same as frontend utils/pathChecks.js


class _Item(BaseModel):
    model_config = ConfigDict(extra="allow")


class SourceReference(_Item):
    doc_id: str | None = None
    doc: str | None = None
    section: str | None = None
    page: int | None = None
    chunk_id: str | None = None
    exact_quote: str | None = None


class Lesson(_Item):
    id: str = Field(min_length=1, max_length=64)
    title: str
    content: str
    minutes: int | None = None
    source_reference: SourceReference | None = None


class Task(_Item):
    id: str = Field(min_length=1, max_length=64)
    title: str
    # Required for publishing (path_checks flags a task without it); optional here so a draft can be saved.
    completion_criteria: str | None = None
    source_reference: SourceReference | None = None


class QuizQuestion(_Item):
    id: str = Field(min_length=1, max_length=64)
    kind: str | None = None
    question: str
    options: list[str] = Field(min_length=2)
    answer: int
    source_reference: SourceReference | None = None

    @model_validator(mode="after")
    def answer_in_range(self) -> "QuizQuestion":
        if not 0 <= self.answer < len(self.options):
            raise ValueError(f"Question {self.id}: answer index out of range")
        return self


class Module(_Item):
    id: str = Field(min_length=1, max_length=64)
    kind: Literal["lesson", "assessment"] = "lesson"
    title: str
    doc_id: str | None = None
    doc_code: str | None = None
    tier: int | None = None
    lessons: list[Lesson] = []
    tasks: list[Task] = []
    quiz: list[QuizQuestion] = []


class Stage(_Item):
    key: str
    modules: list[Module] = []


def _check_unique_ids(stages: list[Stage]) -> list[Stage]:
    """Progress is stored by item id, so a duplicate id would mark two lessons read at once."""
    seen: set[str] = set()
    for stage in stages:
        for module in stage.modules:
            for item_id in [module.id, *(i.id for i in [*module.lessons, *module.tasks, *module.quiz])]:
                if item_id in seen:
                    raise ValueError(f"Duplicate item id in stages: {item_id}")
                seen.add(item_id)
    return stages


class ExcludedChunk(_Item):
    doc: str | None = None
    doc_id: str | None = None
    chunk_id: str
    rule_ids: list[str] = []


class PathContent(BaseModel):
    """Generated content: output of Pipeline 1 (or the frontend draft generator until it is ready)."""

    stages: list[Stage] = Field(min_length=1)
    excluded_chunks: list[ExcludedChunk] = []
    coverage: dict | None = None
    engine: str = Field(default="local-draft", max_length=32)
    model: str | None = Field(default=None, max_length=64)
    prompt_version: str = Field(max_length=16)
    # Pipeline 1 report (set by the server when it generates the content)
    generation: dict | None = None

    @field_validator("stages")
    @classmethod
    def unique_ids(cls, stages: list[Stage]) -> list[Stage]:
        return _check_unique_ids(stages)


class PathCreate(BaseModel):
    job_position_id: str
    level: PathLevel
    purpose: PathPurpose
    source_document_ids: list[str] = Field(min_length=1, max_length=50)
    prompt: str | None = Field(default=None, max_length=4000)
    # Language of learner-facing text written by the model.
    language: Literal["vi", "en"] = "en"
    # Onboarding length; omitted means the full 90-day path. Ignored for promotion paths.
    duration_days: Literal[7, 30, 90] | None = None
    # HR deliberately left out mandatory matrix documents: generate anyway and warn the Reviewer.
    allow_missing_mandatory: bool = False
    # Omit to let the server generate (Gemini, or the rule-based draft without an API key).
    content: PathContent | None = None


class PathRegenerate(BaseModel):
    source_document_ids: list[str] = Field(min_length=1, max_length=50)
    prompt: str | None = Field(default=None, max_length=4000)
    language: Literal["vi", "en"] = "en"
    allow_missing_mandatory: bool = False
    auto_include_missing: bool = False
    content: PathContent | None = None


class PathEdit(BaseModel):
    stages: list[Stage] = Field(min_length=1)
    # What changed, for the audit log, e.g. {"item": "LP-…-L2", "change": "edit_lesson"}
    details: dict[str, str] | None = None

    @field_validator("stages")
    @classmethod
    def unique_ids(cls, stages: list[Stage]) -> list[Stage]:
        return _check_unique_ids(stages)


class PathSubmit(BaseModel):
    """The verification verdict is computed by the server; a inal_status sent by the client is ignored."""

    note: str | None = Field(default=None, max_length=2000)


class RequestChanges(BaseModel):
    message: str = Field(max_length=2000)

    @field_validator("message")
    @classmethod
    def long_enough(cls, value: str) -> str:
        value = value.strip()
        if len(value) < MIN_REASON_LENGTH:
            raise ValueError(f"Feedback must be at least {MIN_REASON_LENGTH} characters")
        return value


class PathApprove(BaseModel):
    departments: list[str] = Field(default=[], max_length=20)
    job_positions: list[str] = Field(default=[], max_length=20)
    # Required unless the server's checks say "verified".
    reason: str | None = Field(default=None, max_length=2000)


class ReasonBody(BaseModel):
    reason: str = Field(max_length=2000)

    @field_validator("reason")
    @classmethod
    def long_enough(cls, value: str) -> str:
        value = value.strip()
        if len(value) < MIN_REASON_LENGTH:
            raise ValueError(f"Reason must be at least {MIN_REASON_LENGTH} characters")
        return value


class ItemRef(BaseModel):
    id: str = Field(max_length=64)
    label: str | None = Field(default=None, max_length=255)


class CommentCreate(BaseModel):
    text: str = Field(max_length=2000)
    item_ref: ItemRef | None = None
    reply_to: str | None = None

    @field_validator("text")
    @classmethod
    def not_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Comment is empty")
        return value


class CommentResolve(BaseModel):
    resolved: bool = True


class Actor(BaseModel):
    id: str
    name: str
    role: UserRole


class CommentOut(BaseModel):
    id: str
    author: Actor | None
    at: datetime
    text: str
    item_ref: dict | None
    reply_to: str | None
    resolved: bool
    resolved_by: Actor | None


class SourceOut(BaseModel):
    document_id: str | None
    code: str
    version: str
    title: str | None = None
    title_en: str | None = None


class Target(BaseModel):
    job_position_id: str
    department_code: str


class PublishedTo(BaseModel):
    departments: list[str]
    job_positions: list[str]


class Approval(BaseModel):
    by: Actor | None
    at: datetime | None
    final_status: FinalStatus | None
    reason: str | None


class PathSummary(BaseModel):
    id: str
    title: str
    title_en: str
    purpose: PathPurpose
    level: PathLevel
    duration_days: int | None = None
    target: Target
    status: PathStatus
    revision: int
    engine: str
    prompt_version: str
    coverage: dict | None
    sources: list[SourceOut]
    module_count: int
    open_comment_count: int
    published_to: PublishedTo | None
    created_by: Actor | None
    created_at: datetime
    updated_at: datetime
    submitted_at: datetime | None
    published_at: datetime | None
    archived_at: datetime | None
    # Actions the current user may take now, so the UI does not duplicate the workflow table.
    allowed_actions: list[str]


class PathOut(PathSummary):
    prompt: str | None
    model: str | None
    generation: dict | None
    stages: list[dict]
    excluded_chunks: list[dict]
    comments: list[CommentOut]
    approval: Approval | None


class AuditLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime
    actor_id: str
    actor_name: str
    actor_role: UserRole
    action: str
    path_id: str | None
    path_title: str | None
    revision: int | None
    status_before: PathStatus | None
    status_after: PathStatus | None
    final_status: FinalStatus | None
    reason: str | None
    details: dict | None


class AuditLogPage(BaseModel):
    items: list[AuditLogOut]
    total: int


class GenerationJobOut(BaseModel):
    """A background generation run. `state.steps` maps sources / analysis / plan / modules / coverage / saving to
    pending | active | done | skipped | failed; `state.modules` follows each module through waiting → lessons → quiz
    → done (or fallback)."""

    id: str
    kind: Literal["create", "regenerate"]
    status: Literal["running", "done", "failed"]
    state: dict
    path_id: str | None
    error: dict | None
    elapsed_ms: int


class PathChecksOut(BaseModel):
    final_status: FinalStatus
    blocking: bool
    reasons: list[dict]
    knowledge: dict[str, int]
    flow_errors: int
    flow_warnings: int
    injection: int
    duplicates: int = 0
    coverage_score: float | None
    mandatory_missing: list[str] = []
    items: list[dict]
    flow: list[dict]
