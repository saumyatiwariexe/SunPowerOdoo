from typing import Annotated

from fastapi import Cookie, Depends
from sqlalchemy.orm import Session

from app.modules.users.models import Role, User

from .config import Settings, get_settings
from .db import get_db
from .errors import AppError
from .security import SESSION_COOKIE, get_session_user_id


def get_current_user(
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
    token: Annotated[str | None, Cookie(alias=SESSION_COOKIE)] = None,
) -> User:
    if not token:
        raise AppError("UNAUTHENTICATED", "Sign in to continue.", 401)
    user = db.get(User, get_session_user_id(token, settings))
    if user is None or not user.active:
        raise AppError("UNAUTHENTICATED", "Sign in to continue.", 401)
    return user


def require_roles(*roles: Role | str):
    allowed = frozenset(Role(role) for role in roles)

    def check_role(user: Annotated[User, Depends(get_current_user)]) -> User:
        if not any(has_role(user, role) for role in allowed):
            raise AppError("FORBIDDEN", "Your role does not allow this action.", 403)
        return user

    return check_role


def has_role(user: User, role: Role | str) -> bool:
    role = Role(role)
    return user.role == role or (role != Role.DIRECTOR and role in user.additional_roles)
