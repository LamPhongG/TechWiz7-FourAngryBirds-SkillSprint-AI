"""Password hashing and JWT access tokens."""
import secrets
from datetime import UTC, datetime, timedelta

import bcrypt
import jwt

from app.core.config import get_settings

# bcrypt only reads the first 72 bytes; longer input raises in bcrypt>=4.1 instead of truncating silently.
_BCRYPT_MAX_BYTES = 72


def hash_password(password: str) -> str:
    raw = password.encode("utf-8")
    if len(raw) > _BCRYPT_MAX_BYTES:
        raise ValueError("Password is too long")
    return bcrypt.hashpw(raw, bcrypt.gensalt()).decode("ascii")


# Letters that are easy to misread in an email (0/O, 1/l/I) are left out; the password is typed by hand.
_PASSWORD_ALPHABETS = ("ABCDEFGHJKLMNPQRSTUVWXYZ", "abcdefghijkmnopqrstuvwxyz", "23456789", "!@#$%*?")


def generate_password(length: int = 12) -> str:
    """Random password with at least one upper-case letter, lower-case letter, digit and symbol (`secrets`, not
    `random`, so it cannot be predicted)."""
    rng = secrets.SystemRandom()
    chars = [rng.choice(a) for a in _PASSWORD_ALPHABETS]
    everything = "".join(_PASSWORD_ALPHABETS)
    chars += [rng.choice(everything) for _ in range(length - len(chars))]
    rng.shuffle(chars)
    return "".join(chars)


def verify_password(password: str, password_hash: str) -> bool:
    raw = password.encode("utf-8")
    if len(raw) > _BCRYPT_MAX_BYTES:
        return False
    return bcrypt.checkpw(raw, password_hash.encode("ascii"))


def create_access_token(user_id: str, user_role: str) -> tuple[str, int]:
    """Sign a token for the user.

    Returns:
        The encoded token and its lifetime in seconds.
    """
    settings = get_settings()
    lifetime = timedelta(minutes=settings.access_token_minutes)
    now = datetime.now(UTC)
    claims = {"sub": user_id, "role": user_role, "iat": now, "exp": now + lifetime}
    token = jwt.encode(claims, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return token, int(lifetime.total_seconds())


def decode_access_token(token: str) -> dict:
    """Return the token claims.

    Raises:
        jwt.InvalidTokenError: signature, expiry or format is invalid.
    """
    settings = get_settings()
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm], options={"require": ["sub", "exp"]})
