from fastapi import APIRouter, HTTPException, status
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from app.api.deps import DbSession

router = APIRouter(tags=["health"])


@router.get("/ping")
def ping() -> dict:
    return {"status": "ok"}


@router.get("/health")
def health(db: DbSession) -> dict:
    """Readiness check for the deploy platform: fails when the database is unreachable."""
    try:
        db.execute(text("SELECT 1"))
    except OperationalError:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database unavailable") from None
    return {"status": "ok", "database": "ok"}
