from functools import lru_cache
from threading import Lock
from time import monotonic

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.pagination import Pagination
from app.core.security import hash_password, verify_password

from .models import Role, User, UserRoleGrant
from .schemas import StaffCreate, StaffPatch

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


def list_staff(db: Session, paging: Pagination) -> tuple[list[User], int]:
    total = db.scalar(select(func.count()).select_from(User)) or 0
    query = select(User).order_by(User.name, User.id).offset(paging.offset).limit(paging.page_size)
    return list(db.scalars(query)), total


def assignment_options(db: Session, paging: Pagination, role: Role | None = None) -> tuple[list[dict], int]:
    eligible = (role,) if role is not None else (Role.CREW, Role.SUPPORT, Role.DIRECTOR)
    filters = (User.active.is_(True), or_(
        User.role.in_(eligible),
        User.role_grants.any(UserRoleGrant.role.in_(eligible)),
    ))
    total = db.scalar(select(func.count()).select_from(User).where(*filters)) or 0
    query = select(User).where(*filters).order_by(User.name, User.id)
    rows = db.scalars(query.offset(paging.offset).limit(paging.page_size))
    return [dict(id=row.id, name=row.name, email=row.email, role=row.role) for row in rows], total


def get_staff(db: Session, user_id: int, *, for_update: bool = False) -> User:
    user = db.get(User, user_id, with_for_update=for_update, populate_existing=for_update)
    if user is None:
        raise AppError("USER_NOT_FOUND", "Staff account not found.", 404)
    return user


def _flush_staff(db: Session) -> None:
    try:
        db.flush()
    except IntegrityError as exc:
        constraint = getattr(getattr(exc.orig, "diag", None), "constraint_name", None)
        if constraint == "users_email_key" or "UNIQUE constraint failed: users.email" in str(exc.orig):
            raise AppError("EMAIL_IN_USE", "A staff account already uses this email.", 409) from exc
        raise


def create_staff(db: Session, payload: StaffCreate) -> User:
    user = User(**payload.model_dump(exclude={"password", "additional_roles"}), password_hash=hash_password(payload.password))
    user.role_grants = [UserRoleGrant(role=role) for role in payload.additional_roles]
    db.add(user)
    _flush_staff(db)
    return user


def update_staff(db: Session, user_id: int, payload: StaffPatch, actor: User) -> User:
    changes = payload.model_dump(exclude_unset=True)
    grants = changes.pop("additional_roles", None)
    if {"role", "active"} & changes.keys():
        # Serialize access changes so concurrent edits cannot remove the final director.
        directors = list(db.scalars(select(User.id).where(
            User.role == Role.DIRECTOR, User.active.is_(True)
        ).order_by(User.id).with_for_update()))
        if actor.id not in directors:
            raise AppError("FORBIDDEN", "Director access is required.", 403)
        losing_access = changes.get("role", Role.DIRECTOR) != Role.DIRECTOR or changes.get("active") is False
        if directors == [user_id] and losing_access:
            raise AppError("LAST_DIRECTOR", "Keep at least one active director.", 409)
    user = get_staff(db, user_id, for_update=True)
    if grants is not None:
        if changes.get("role", user.role) == Role.DIRECTOR and grants:
            raise AppError("INVALID_ROLE_GRANT", "Director accounts do not need extra roles.", 409)
        if changes.get("role", user.role) in grants:
            raise AppError("INVALID_ROLE_GRANT", "An extra role cannot match the primary role.", 409)
        requested = set(grants)
        user.role_grants = [grant for grant in user.role_grants if grant.role in requested]
        existing = {grant.role for grant in user.role_grants}
        user.role_grants.extend(UserRoleGrant(role=role) for role in requested - existing)
    for field, value in changes.items():
        setattr(user, field, value)
    if changes.get("role") == Role.DIRECTOR:
        user.role_grants.clear()
    elif changes.get("role") is not None and grants is None:
        user.role_grants = [grant for grant in user.role_grants if grant.role != user.role]
    _flush_staff(db)
    return user
