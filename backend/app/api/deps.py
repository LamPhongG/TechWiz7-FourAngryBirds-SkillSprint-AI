"""Shared FastAPI dependencies: DB session, current user, role guard."""
from collections.abc import Callable
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db.session import get_db
from app.models import User, UserRole

DbSession = Annotated[Session, Depends(get_db)]

# auto_error=False so a missing header returns our 401 (FastAPI's default is 403, which misleads the client).
_bearer = HTTPBearer(auto_error=False)


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(status.HTTP_401_UNAUTHORIZED, detail=detail, headers={"WWW-Authenticate": "Bearer"})


def get_current_user(
    db: DbSession,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> User:
    if credentials is None:
        raise _unauthorized("Not authenticated")
    try:
        claims = decode_access_token(credentials.credentials)
    except jwt.ExpiredSignatureError:
        raise _unauthorized("Session expired") from None
    except jwt.InvalidTokenError:
        raise _unauthorized("Invalid token") from None
    user = db.get(User, claims["sub"])
    # A deactivated account must lose access immediately, not when its token expires.
    if user is None or not user.is_active:
        raise _unauthorized("Account not found or disabled")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_roles(*roles: UserRole) -> Callable[[User], User]:
    """Dependency that lets only the given roles through, e.g. `Depends(require_roles(UserRole.HR))`."""

    def guard(user: CurrentUser) -> User:
        if user.user_role not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail="This action is not allowed for your role")
        return user

    return guard
