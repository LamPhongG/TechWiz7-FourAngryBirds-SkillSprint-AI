"""Mounts every route module under the API prefix. Add new routers here."""
from fastapi import APIRouter

from app.api.routes import audit, auth, catalog, documents, enrollments, health, paths, reports, users

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(catalog.router)
api_router.include_router(documents.router)
api_router.include_router(paths.router)
api_router.include_router(enrollments.router)
api_router.include_router(audit.router)
api_router.include_router(reports.router, prefix="/reports", tags=["reports"])
