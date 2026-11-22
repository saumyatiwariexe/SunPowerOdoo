from typing import Annotated, Literal
from urllib.parse import urlsplit
from fastapi import APIRouter, Cookie, Depends, Request, Response
from sqlalchemy.orm import Session
from app.core.config import Settings, get_settings
from app.core.db import get_db
from app.core.deps import require_roles
from app.core.errors import AppError
from app.modules.users.models import User
from . import auth, service
from .models import CustomerAccount
from .schemas import ActivateRequest, CustomerLogin, InviteRequest, ServiceRequest

router = APIRouter(prefix="/customer", tags=["customer portal"])
staff_router = APIRouter(prefix="/customer-management", tags=["customer onboarding"])
Db = Annotated[Session, Depends(get_db)]
Config = Annotated[Settings, Depends(get_settings)]
Agent = Annotated[User, Depends(require_roles("DIRECTOR", "SALES"))]


def current_account(db: Db, settings: Config, token: Annotated[str | None, Cookie(alias=service.COOKIE)] = None):
    if not token:
        raise AppError("UNAUTHENTICATED", "Sign in to view your solar projects.", 401)
    return auth.session_account(db, token, settings)


Account = Annotated[CustomerAccount, Depends(current_account)]


def limit(request, action, identity=None):
    limiter = request.app.state.login_rate_limiter
    limiter.check(f"customer:{action}:ip:{request.client.host if request.client else 'unknown'}")
    if identity:
        limiter.check(f"customer:{action}:identity:{identity}")


def cookie(response, account, settings):
    response.set_cookie(service.COOKIE, auth.issue_session(account.id, settings), max_age=7200,
                        path=service.COOKIE_PATH, httponly=True, secure=settings.secure_cookies, samesite="lax")
    response.headers["Cache-Control"] = "no-store"


@staff_router.get("/leads/{lead_id}")
def account_status(lead_id: int, db: Db, actor: Agent, settings: Config):
    _, account = auth.lead_account(db, lead_id)
    origin = settings.customer_portal_url or ""
    return {"data": {**auth.account_status(account),
                     "login_url": origin.rstrip("/") + "/customer" if origin else None,
                     "local_only": urlsplit(origin).hostname in ("localhost", "127.0.0.1", "::1")}}


@staff_router.post("/leads/{lead_id}/invite")
def invite(lead_id: int, payload: InviteRequest, db: Db, actor: Agent, settings: Config, request: Request):
    limit(request, "invite", str(actor.id))
    auth.email_config(settings)
    account, password = auth.invite(db, lead_id, payload.email, actor.id)
    data = auth.account_status(account)
    # Persist only the password hash before sending; a failed send can be retried.
    db.commit()
    auth.send_invite(settings, payload.email, password)
    return {"data": {**data, "message": "Login details accepted by SendGrid. Ask the customer to check their inbox."}}


@router.post("/auth/activate")
def activate(payload: ActivateRequest, db: Db, request: Request, response: Response, settings: Config):
    limit(request, "activate")
    account = auth.activate(db, payload.token, payload.password)
    db.commit()
    cookie(response, account, settings)
    return {"data": {"email": account.email}}


@router.post("/auth/login")
def login(payload: CustomerLogin, db: Db, request: Request, response: Response, settings: Config):
    limit(request, "login", payload.email)
    account = auth.authenticate(db, payload.email, payload.password)
    db.commit()
    cookie(response, account, settings)
    return {"data": {"email": account.email}}


@router.post("/auth/logout")
def logout(response: Response, settings: Config):
    response.delete_cookie(service.COOKIE, path=service.COOKIE_PATH, secure=settings.secure_cookies, httponly=True, samesite="lax")
    return {"data": None}


@router.get("/overview")
def overview(db: Db, account: Account, response: Response):
    response.headers["Cache-Control"] = "private, no-store"
    return {"data": service.overview(db, account.customer_id)}


@router.get("/documents/{kind}/{record_id}")
def document(kind: Literal["quotes", "invoices"], record_id: int, db: Db, account: Account, response: Response):
    response.headers["Cache-Control"] = "private, no-store"
    return {"data": service.document(db, kind, record_id, account.customer_id)}


@router.post("/tickets", status_code=201)
def request_service(payload: ServiceRequest, db: Db, account: Account):
    data = service.request_service(db, account.customer_id, payload)
    db.commit()
    return {"data": data}
