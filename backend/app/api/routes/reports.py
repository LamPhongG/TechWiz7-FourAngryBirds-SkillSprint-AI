"""Reports center: HR, Reviewers and Admins."""
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import Response

from app.api.deps import DbSession, require_roles
from app.models import User, UserRole
from app.schemas.reports import AlertRow, ComparisonSummaryRow, DocumentReportRow, QuizAnalyticsRow, RoleCoverageRow
from app.services import reports as service

router = APIRouter()
Reporter = Annotated[User, Depends(require_roles(UserRole.HR, UserRole.REVIEWER, UserRole.ADMIN))]


@router.get("/role-coverage", response_model=list[RoleCoverageRow])
def role_coverage(db: DbSession, user: Reporter):
    return service.role_coverage(db)


@router.get("/quiz-analytics", response_model=list[QuizAnalyticsRow])
def quiz_analytics(db: DbSession, user: Reporter):
    return service.quiz_analytics(db)


@router.get("/documents", response_model=list[DocumentReportRow])
def documents_report(db: DbSession, user: Reporter):
    return service.documents_report(db)


@router.get("/alerts", response_model=list[AlertRow])
def alerts(db: DbSession, user: Reporter):
    return service.alerts(db)


@router.get("/comparison", response_model=list[ComparisonSummaryRow])
def comparison_summary(db: DbSession, user: Reporter):
    return service.comparison_summary(db)


@router.get("/comparison.csv")
def comparison_csv(db: DbSession, user: Reporter):
    # UTF-8 BOM so spreadsheet applications open the CSV correctly.
    return Response("\ufeff" + service.comparison_csv(db), media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": 'attachment; filename="genai_python_comparison.csv"'})
