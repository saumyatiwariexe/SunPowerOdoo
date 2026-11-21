from functools import lru_cache
from threading import Lock
from time import monotonic

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.security import hash_password, verify_password

from .models import User

LOGIN_WINDOW_SECONDS = 60
LOGIN_ATTEMPTS_PER_WINDOW = 10


class LoginRateLimiter:
    def __init__(self):
        self._clients: dict[str, tuple[float, int]] = {}
        self._lock = Lock()
        self._last_cleanup = 0.0

    def check(self, client: str) -> None:
        with self._lock:
            now = monotonic()
            if now - self._last_cleanup >= LOGIN_WINDOW_SECONDS:
                self._clients = {
                    key: entry for key, entry in self._clients.items() if entry[0] > now
                }
                self._last_cleanup = now

            expires_at, count = self._clients.get(client, (0.0, 0))
            if now >= expires_at:
                expires_at, count = now + LOGIN_WINDOW_SECONDS, 0
            if count >= LOGIN_ATTEMPTS_PER_WINDOW:
                raise AppError("LOGIN_RATE_LIMIT", "Too many sign-in attempts. Try again shortly.", 429)
            self._clients[client] = (expires_at, count + 1)


@lru_cache
def _dummy_password_hash() -> str:
    return hash_password("unused-account-password")


def authenticate(db: Session, email: str, password: str) -> User:
    user = db.scalar(select(User).where(User.email == email))
    password_hash = user.password_hash if user is not None else _dummy_password_hash()
    valid = verify_password(password, password_hash)
    if user is None or not user.active or not valid:
        raise AppError("INVALID_CREDENTIALS", "Invalid email or password.", 401)
    return user
