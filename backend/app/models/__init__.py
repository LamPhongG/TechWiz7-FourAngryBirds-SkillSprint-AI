"""ORM models. Importing this package registers every table on `Base.metadata` (Alembic relies on it)."""
from app.models.audit import AuditLog
from app.models.document import Document, DocumentChunk, InjectionFlag
from app.models.enrollment import Enrollment, QuizAttempt
from app.models.enums import (
    AssignmentSource,
    EnrollmentStatus,
    FinalStatus,
    PathLevel,
    PathPurpose,
    PathStatus,
    Priority,
    ProcessingStatus,
    TrainingStatus,
    UserRole,
)
from app.models.learning_path import LearningPath, PathAssignment, PathComment, PathSource
from app.models.organization import Department, JobPosition, RoleRequirement, User

__all__ = [
    "AssignmentSource",
    "AuditLog",
    "Department",
    "Document",
    "DocumentChunk",
    "Enrollment",
    "EnrollmentStatus",
    "FinalStatus",
    "InjectionFlag",
    "JobPosition",
    "LearningPath",
    "PathAssignment",
    "PathComment",
    "PathLevel",
    "PathPurpose",
    "PathSource",
    "PathStatus",
    "Priority",
    "ProcessingStatus",
    "QuizAttempt",
    "RoleRequirement",
    "TrainingStatus",
    "User",
    "UserRole",
]
