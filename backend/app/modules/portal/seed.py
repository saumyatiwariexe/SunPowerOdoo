"""Explicit demo accounts only; never onboard real enquiry customers here."""
from datetime import UTC, datetime
from sqlalchemy import select
from app.core.security import hash_password
from app.modules.users.models import Customer, User
from .models import CustomerAccount


def seed_sample_accounts(db, password):
    actor = db.scalar(select(User).where(User.role == "DIRECTOR", User.active.is_(True)).order_by(User.id))
    if not actor:
        return
    existing = set(db.scalars(select(CustomerAccount.customer_id)))
    customers = list(db.scalars(select(Customer).where(Customer.email.like("sample.customer.%@sunpower.invalid"))))
    missing = [customer for customer in customers if customer.id not in existing]
    if not missing:
        return
    password_hash = hash_password(password)
    for customer in missing:
        db.add(CustomerAccount(customer_id=customer.id, email=customer.email, password_hash=password_hash,
                               invited_by_id=actor.id, activated_at=datetime.now(UTC)))
    db.flush()
