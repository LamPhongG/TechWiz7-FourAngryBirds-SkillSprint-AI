from typing import Literal
from pydantic import BaseModel, Field


class SourceCitation(BaseModel):
    doc_id: str
    source_file: str
    page_number: int
    section_heading: str
    exact_quote: str


class RubricCriterionSchema(BaseModel):
    """Structured rubric criterion for practical assessments."""
    criterion: str
    weight: float = Field(default=1.0, description="Relative weight or percentage for scoring")
    expected_performance: str = Field(description="Benchmark of successful execution")
    pass_condition: str = Field(description="Specific threshold required to pass")


class QuizQuestionSchema(BaseModel):
    question_id: str
    question_text: str
    options: list[str]
    correct_answer: str
    explanation: str
    difficulty: Literal["Beginner", "Intermediate", "Advanced"] = Field(
        default="Intermediate",
        description="Difficulty level based on role and experience",
    )
    source_citation: SourceCitation


class TaskSchema(BaseModel):
    task_id: str
    title: str
    description: str
    estimated_minutes: int
    difficulty: Literal["Beginner", "Intermediate", "Advanced"] = Field(
        default="Intermediate",
        description="Task difficulty level",
    )
    source_citation: SourceCitation


class ModuleSchema(BaseModel):
    module_id: str
    title: str
    description: str
    order_index: int
    difficulty: Literal["Beginner", "Intermediate", "Advanced"] = Field(
        default="Intermediate",
        description="Overall module difficulty",
    )
    tasks: list[TaskSchema] = Field(default_factory=list)
    quizzes: list[QuizQuestionSchema] = Field(default_factory=list)
    rubric: list[RubricCriterionSchema] = Field(
        default_factory=list,
        description="Assessment rubrics for practical or scenario evaluations",
    )
    source_citation: SourceCitation


class OnboardingPlanSchema(BaseModel):
    plan_id: str
    target_role: str
    title: str
    summary: str
    prompt_version: str
    modules: list[ModuleSchema]
    source_citation: SourceCitation
