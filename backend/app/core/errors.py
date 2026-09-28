"""Business errors with a stable code the frontend can translate."""
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class AppError(Exception):
    """Raised by services; rendered as `{"detail": message, "code": code, "vars": {...}}`.

    `code` reuses the frontend i18n keys (e.g. `err_duplicate_file`) so the UI can show a localised
    message; `detail` stays a plain string because frontend `apiClient.js` reads it as the fallback.
    """

    # Positional-only so params may themselves be called `code` (e.g. the duplicate document's code).
    def __init__(self, status_code: int, code: str, message: str, /, **params):
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.params = params


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(_request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.message, "code": exc.code, "vars": exc.params},
        )
