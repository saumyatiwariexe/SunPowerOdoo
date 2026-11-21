from datetime import UTC, datetime, timedelta

import bcrypt
import jwt

from .config import Settings
from .errors import AppError

SESSION_COOKIE = "sunpower_session"
SESSION_COOKIE_PATH = "/api/v1"


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("ascii")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("ascii"))
    except (ValueError, UnicodeError):
        return False


def _jwt_secret(settings: Settings) -> str:
    if settings.jwt_secret is None:
        raise AppError("AUTH_UNAVAILABLE", "Authentication is not configured.", 503)
    return settings.jwt_secret.get_secret_value()


def create_session_token(user_id: int, settings: Settings) -> str:
    now = datetime.now(UTC)
    return jwt.encode(
        {"sub": str(user_id), "iat": now, "exp": now + timedelta(seconds=settings.jwt_ttl_seconds)},
        _jwt_secret(settings),
        algorithm="HS256",
    )


def get_session_user_id(token: str, settings: Settings) -> int:
    try:
        claims = jwt.decode(
            token,
            _jwt_secret(settings),
            algorithms=["HS256"],
            options={"require": ["sub", "iat", "exp"]},
        )
        user_id = int(claims["sub"])
    except (jwt.InvalidTokenError, ValueError) as exc:
        raise AppError("UNAUTHENTICATED", "Sign in to continue.", 401) from exc
    if not 0 < user_id <= 2_147_483_647:
        raise AppError("UNAUTHENTICATED", "Sign in to continue.", 401)
    return user_id
