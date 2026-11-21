from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.db import get_db
from app.core.deps import get_current_user
from app.core.security import SESSION_COOKIE, SESSION_COOKIE_PATH, create_session_token

from .models import User
from .schemas import LoginRequest, UserRead
from .service import authenticate

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login")
def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict[str, UserRead]:
    request.app.state.login_rate_limiter.check(request.client.host if request.client else "unknown")
    user = authenticate(db, payload.email, payload.password)
    response.set_cookie(
        SESSION_COOKIE,
        create_session_token(user.id, settings),
        max_age=settings.jwt_ttl_seconds,
        path=SESSION_COOKIE_PATH,
        httponly=True,
        secure=settings.secure_cookies,
        samesite="lax",
    )
    return {"data": UserRead.model_validate(user)}


@router.post("/logout", dependencies=[Depends(get_current_user)])
def logout(
    response: Response,
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict[str, None]:
    response.delete_cookie(
        SESSION_COOKIE,
        path=SESSION_COOKIE_PATH,
        httponly=True,
        secure=settings.secure_cookies,
        samesite="lax",
    )
    return {"data": None}


@router.get("/me")
def me(user: Annotated[User, Depends(get_current_user)]) -> dict[str, UserRead]:
    return {"data": UserRead.model_validate(user)}
