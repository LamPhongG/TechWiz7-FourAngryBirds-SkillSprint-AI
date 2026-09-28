"""Who can see which learning paths and documents. One place, so list and detail endpoints agree."""
from sqlalchemy import ColumnElement, and_, exists, false, or_, select, true

from app.models import Document, Enrollment, EnrollmentStatus, LearningPath, PathSource, PathStatus, User, UserRole

COMPANY_WIDE = "Company-wide"
# Test documents (injection / contradiction samples) exist for QA, not for employees to read.
HIDDEN_FROM_EMPLOYEES = ("Test Case",)


def path_filter(user: User) -> ColumnElement[bool]:
    """HR and Admins see every path (Admins read only, SRS Step 51), Reviewers everything past draft, employees the
    published paths assigned to them."""
    if user.user_role in (UserRole.HR, UserRole.ADMIN):
        return true()
    if user.user_role is UserRole.REVIEWER:
        return LearningPath.status != PathStatus.DRAFT
    if user.user_role is UserRole.EMPLOYEE:
        assigned = exists().where(Enrollment.path_id == LearningPath.id, Enrollment.user_id == user.id,
                                  Enrollment.status != EnrollmentStatus.WITHDRAWN)
        return and_(LearningPath.status == PathStatus.PUBLISHED, assigned)
    return false()


def document_filter(user: User) -> ColumnElement[bool]:
    """Employees see company-wide documents, their department's, and sources of paths assigned to them."""
    if user.user_role in (UserRole.HR, UserRole.REVIEWER, UserRole.ADMIN):
        return true()
    if user.user_role is UserRole.EMPLOYEE:
        sources_of_my_paths = (
            select(PathSource.document_id)
            .join(LearningPath, LearningPath.id == PathSource.path_id)
            .where(path_filter(user), PathSource.document_id.is_not(None))
        )
        return and_(
            Document.category.not_in(HIDDEN_FROM_EMPLOYEES),
            or_(Document.department_code.in_([COMPANY_WIDE, user.department_code]), Document.id.in_(sources_of_my_paths)),
        )
    return false()
