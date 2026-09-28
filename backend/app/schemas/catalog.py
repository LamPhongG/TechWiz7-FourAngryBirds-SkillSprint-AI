"""Departments, job positions and the Role Requirement Matrix."""
from typing import Literal

from pydantic import BaseModel, ConfigDict


class DepartmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    code: str
    name: str
    name_en: str


class JobPositionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    name_en: str
    department_code: str
    requirement_count: int = 0
    mandatory_count: int = 0


class SourceDocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    code: str
    version: str
    title: str
    title_en: str
    processing_status: str


class RequiredSourceOut(BaseModel):
    """A document the Role Requirement Matrix cites for a position (SRS Step 10 and 28).

    `mandatory` documents must be among the sources of the position's learning path.
    """

    code: str
    mandatory: bool
    # ready: the version in force is processed and selectable; not_ready: it is still processing or failed;
    # missing: no version of the document is in force in the repository.
    status: Literal["ready", "not_ready", "missing"]
    document: SourceDocumentOut | None
    requirement_ids: list[str]
    mandatory_requirement_ids: list[str]
    # Rows written against an older version than the one in force; their wording must be re-checked.
    outdated_requirement_ids: list[str]
