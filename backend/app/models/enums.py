"""Enum values shared by the ORM, the API schemas and the frontend (keep the strings in sync)."""
from enum import StrEnum


class UserRole(StrEnum):
    ADMIN = "admin"
    HR = "hr"
    REVIEWER = "reviewer"
    EMPLOYEE = "employee"


class ProcessingStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class PathStatus(StrEnum):
    DRAFT = "draft"
    IN_REVIEW = "in_review"
    CHANGES_REQUESTED = "changes_requested"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class PathPurpose(StrEnum):
    ONBOARDING = "onboarding"
    PROMOTION = "promotion"


class PathLevel(StrEnum):
    BEGINNER = "Beginner"
    INTERMEDIATE = "Intermediate"
    ADVANCED = "Advanced"


class FinalStatus(StrEnum):
    """Verification verdict (`final_status` in frontend `utils/pathChecks.js`)."""

    VERIFIED = "verified"
    VERIFIED_WARNING = "verified_warning"
    MANUAL_REVIEW = "manual_review"


class TrainingStatus(StrEnum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class EnrollmentStatus(StrEnum):
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    WITHDRAWN = "withdrawn"


class AssignmentSource(StrEnum):
    AUTO_DEPARTMENT = "auto_department"
    AUTO_POSITION = "auto_position"
    MANUAL = "manual"
    # The employee enrolled from "Explore paths" (optional path, no due date).
    SELF = "self"


class Priority(StrEnum):
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"