from typing import Annotated

from fastapi import APIRouter, Depends, Path, Request, Response
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.db import get_db
from app.core.deps import get_current_user, require_roles
from app.core.pagination import Pagination
from app.core.security import SESSION_COOKIE, SESSION_COOKIE_PATH, create_session_token

from .models import User
from .schemas import LoginRequest, StaffCreate, StaffPage, StaffPatch, StaffRead, UserRead
from .service import authenticate, create_staff, get_staff, list_staff, update_staff

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


director = Depends(require_roles("DIRECTOR"))
staff_router = APIRouter(prefix="/users", tags=["staff"], dependencies=[director])
Db = Annotated[Session, Depends(get_db)]
StaffId = Annotated[int, Path(gt=0, le=2_147_483_647)]


@staff_router.get("")
def staff(db: Db, paging: Annotated[Pagination, Depends()]) -> StaffPage:
    rows, total = list_staff(db, paging)
    return StaffPage(data=[StaffRead.model_validate(row) for row in rows], meta=paging.meta(total))


@staff_router.get("/{user_id}")
def staff_detail(user_id: StaffId, db: Db) -> dict[str, StaffRead]:
    return {"data": StaffRead.model_validate(get_staff(db, user_id))}


@staff_router.post("", status_code=201)
def add_staff(payload: StaffCreate, db: Db) -> dict[str, StaffRead]:
    data = StaffRead.model_validate(create_staff(db, payload))
    db.commit()
    return {"data": data}


@staff_router.patch("/{user_id}")
def edit_staff(user_id: StaffId, payload: StaffPatch, db: Db, actor: Annotated[User, director]) -> dict[str, StaffRead]:
    data = StaffRead.model_validate(update_staff(db, user_id, payload, actor))
    db.commit()
    return {"data": data}
