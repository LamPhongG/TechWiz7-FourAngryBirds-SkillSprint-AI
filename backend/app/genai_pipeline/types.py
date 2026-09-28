"""Inputs of the generation pipeline. Plain data, so the pipeline never touches the database."""
from dataclasses import dataclass, field

STAGE_TEMPLATES = {
    "onboarding": ("day1", "week1", "week2", "day30", "day60", "day90"),
    "promotion": ("foundation", "deep", "practice", "assessment"),
}
# Onboarding length chosen by HR (SRS Step 13) → the milestones it keeps, always a prefix of the full template.
ONBOARDING_DURATIONS = {
    7: ("day1", "week1"),
    30: ("day1", "week1", "week2", "day30"),
    90: STAGE_TEMPLATES["onboarding"],
}
DEFAULT_ONBOARDING_DAYS = 90
# How the model is told when a module is studied, so tasks fit the time the learner has.
STAGE_TIMING = {
    "day1": "on day 1", "week1": "during week 1", "week2": "during week 2", "day30": "by day 30",
    "day60": "by day 60", "day90": "by day 90", "foundation": "in the foundation phase",
    "deep": "in the deep-dive phase", "practice": "in the practice phase", "assessment": "in the assessment phase",
}


def stage_template(purpose: str, duration_days: int | None = None) -> tuple[str, ...]:
    """Stages a path may use. Promotion paths are phase-based, so a duration only shortens onboarding."""
    if purpose == "onboarding":
        return ONBOARDING_DURATIONS[duration_days or DEFAULT_ONBOARDING_DAYS]
    return STAGE_TEMPLATES.get(purpose, STAGE_TEMPLATES["onboarding"])
QUIZ_PER_MODULE = {"Beginner": 3, "Intermediate": 4, "Advanced": 5}
TASKS_PER_MODULE = {"Beginner": 1, "Intermediate": 2, "Advanced": 3}


@dataclass
class SourceDoc:
    id: str
    code: str
    version: str
    title: str
    title_en: str
    category: str
    department: str
    chunks: list[dict]
    flags: list[dict] = field(default_factory=list)
    # Every heading of the document, parents included (`ingestion.chunker.outline`); lets the role filter see that
    # "3.1 Mission" sits under "3. Sales Executive".
    outline: list[str] = field(default_factory=list)


@dataclass
class RoleScope:
    """Who the path is for, and who else exists: the role filter sets aside sections that belong to the others."""

    role: str
    department: str
    other_roles: list[str]
    other_departments: list[str]


@dataclass
class GenerationRequest:
    path_id: str
    purpose: str
    level: str
    role_name: str
    role_name_en: str
    department: str
    prompt_version: str
    language: str = "en"
    hr_prompt: str | None = None
    # Onboarding only: 7, 30 or 90 days; None means the full 90-day template.
    duration_days: int | None = None
    # The role's Role Requirement Matrix rows (`services.role_matrix.as_generation_dict`); empty when none.
    requirements: list[dict] = field(default_factory=list)
    # None: every chunk of every source is used (no role filtering).
    scope: RoleScope | None = None


def doc_tier(doc: SourceDoc) -> int:
    """Company foundations first, department practice later (frontend `docTier`)."""
    if doc.category == "Handbook":
        return 0
    if doc.category in ("Policy", "Compliance") and doc.department == "Company-wide":
        return 1
    if doc.category in ("Policy", "Compliance", "Role Description"):
        return 2
    if doc.category in ("SOP", "Process Manual"):
        return 3
    return 4
