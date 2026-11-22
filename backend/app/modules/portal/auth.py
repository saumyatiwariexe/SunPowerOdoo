"""Agent-controlled customer invitations and separate customer sessions."""
import hashlib
import json
import secrets
from datetime import UTC, datetime, timedelta
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

import jwt
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from app.core.errors import AppError
from app.core.security import _jwt_secret, hash_password, verify_password
from app.modules.leads.models import Lead
from .models import CustomerAccount


def email_config(settings):
    if not all((settings.sendgrid_api_key, settings.sendgrid_from_email, settings.customer_portal_url)):
        raise AppError("EMAIL_NOT_CONFIGURED", "Configure SendGrid and the customer portal URL before inviting clients.", 503)
    url = urlsplit(settings.customer_portal_url)
    if url.scheme not in ("http", "https") or not url.netloc or url.path not in ("", "/") or url.query or url.fragment:
        raise AppError("EMAIL_NOT_CONFIGURED", "Customer portal URL must be a valid site origin.", 503)


def lead_account(db, lead_id):
    lead = db.get(Lead, lead_id)
    if lead is None:
        raise AppError("NOT_FOUND", "Lead not found.", 404)
    account = db.scalar(select(CustomerAccount).where(CustomerAccount.customer_id == lead.customer_id))
    return lead, account


def account_status(account):
    return {"status": "ACTIVE" if account and account.activated_at else "INVITED" if account else "NOT_INVITED",
            "email": account.email if account else None}


def invite(db, lead_id, email, actor_id):
    # Lock the customer lead while creating/resending an invitation.
    lead = db.get(Lead, lead_id, with_for_update=True)
    if lead is None:
        raise AppError("NOT_FOUND", "Lead not found.", 404)
    if lead.status in ("NEW", "LOST"):
        raise AppError("LEAD_NOT_READY", "Contact and qualify this lead before granting portal access.", 409)
    account = db.scalar(select(CustomerAccount).where(CustomerAccount.customer_id == lead.customer_id).with_for_update())
    if account and account.activated_at:
        raise AppError("ALREADY_ONBOARDED", "This customer already has an active portal account.", 409)
    if account is None:
        account = CustomerAccount(customer_id=lead.customer_id, email=email, invited_by_id=actor_id)
        db.add(account)
    password = secrets.token_urlsafe(18)
    account.email = email
    account.password_hash = hash_password(password)
    account.invite_hash = None
    account.invite_expires_at = datetime.now(UTC) + timedelta(hours=24)
    account.invited_by_id = actor_id
    try:
        db.flush()
    except IntegrityError:
        raise AppError("ACCOUNT_CONFLICT", "This email or customer already has a portal account. Check the existing account.", 409) from None
    return account, password


def send_invite(settings, email, password):
    email_config(settings)
    link = settings.customer_portal_url.rstrip("/") + "/customer"
    body = {
        "personalizations": [{"to": [{"email": email}]}],
        "from": {"email": settings.sendgrid_from_email, "name": "SunPower Solutions"},
        "subject": "Your SunPower customer login details",
        "content": [{"type": "text/plain", "value":
            f"Your SunPower agent has invited you to My solar.\n\nSign-in email: {email}\n"
            f"Password: {password}\nSign in: {link}\n\n"
            "No password setup or reset is required. Sign in for the first time within 24 hours. "
            "After your first sign-in, keep using these credentials. If this email expires before you sign in, ask your agent to resend it.\n\n"
            "View your installation, documents, warranties and service requests. "
            "If you were not expecting this invitation, ignore this email.\n"}],
        "tracking_settings": {"click_tracking": {"enable": False, "enable_text": False},
                              "open_tracking": {"enable": False}},
    }
    request = Request("https://api.sendgrid.com/v3/mail/send", data=json.dumps(body).encode(),
                      headers={"Authorization": "Bearer " + settings.sendgrid_api_key.get_secret_value(),
                               "Content-Type": "application/json"}, method="POST")
    try:
        with urlopen(request, timeout=15) as response:
            if response.status != 202:
                raise AppError("EMAIL_UNAVAILABLE", "Email was not accepted. Retry the invitation.", 503)
    except (HTTPError, URLError, TimeoutError):
        raise AppError("EMAIL_UNAVAILABLE", "Invitation saved, but email could not be confirmed. Retry the invitation.", 503) from None


def activate(db, token, password):
    account = db.scalar(select(CustomerAccount).where(
        CustomerAccount.invite_hash == hashlib.sha256(token.encode()).hexdigest()).with_for_update())
    if not account or account.activated_at or not account.invite_expires_at or account.invite_expires_at <= datetime.now(UTC):
        raise AppError("INVALID_INVITATION", "This invitation is invalid or expired. Ask your agent to resend it.", 400)
    account.password_hash = hash_password(password)
    account.activated_at = datetime.now(UTC)
    account.invite_hash = None
    account.invite_expires_at = None
    db.flush()
    return account


def authenticate(db, email, password):
    account = db.scalar(select(CustomerAccount).where(CustomerAccount.email == email).with_for_update())
    if not account or not account.password_hash or not verify_password(password, account.password_hash):
        raise AppError("INVALID_CREDENTIALS", "Email or password is incorrect, or the initial login has expired. Ask your agent for help.", 401)
    if not account.activated_at:
        if not account.invite_expires_at or account.invite_expires_at <= datetime.now(UTC):
            raise AppError("INVALID_CREDENTIALS", "Email or password is incorrect, or the initial login has expired. Ask your agent for help.", 401)
        account.activated_at = datetime.now(UTC)
        account.invite_hash = None
        account.invite_expires_at = None
        db.flush()
    return account


def issue_session(account_id, settings):
    now = datetime.now(UTC)
    return jwt.encode({"sub": str(account_id), "aud": "sunpower-customer", "iat": now,
                       "exp": now + timedelta(hours=2)}, _jwt_secret(settings), algorithm="HS256")


def session_account(db, token, settings):
    try:
        claims = jwt.decode(token, _jwt_secret(settings), algorithms=["HS256"], audience="sunpower-customer",
                            options={"require": ["sub", "aud", "iat", "exp"]})
        account_id = int(claims["sub"])
        if not 0 < account_id <= 2_147_483_647:
            raise ValueError()
    except (jwt.InvalidTokenError, ValueError, TypeError):
        raise AppError("UNAUTHENTICATED", "Sign in to view your solar projects.", 401) from None
    account = db.get(CustomerAccount, account_id)
    if not account or not account.activated_at:
        raise AppError("UNAUTHENTICATED", "Sign in to view your solar projects.", 401)
    return account
