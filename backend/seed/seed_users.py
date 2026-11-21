from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.modules.users.models import Role, User


def seed_users(db: Session, password: str) -> None:
    demo_emails = {role: f"{role.lower()}@sunpower.test" for role in Role}
    existing = set(db.scalars(select(User.email).where(User.email.in_(demo_emails.values()))))
    missing = {role: email for role, email in demo_emails.items() if email not in existing}
    if missing:
        password_hash = hash_password(password)
        db.add_all(
            User(name=f"Demo {role.title()}", email=email, role=role, password_hash=password_hash)
            for role, email in missing.items()
        )
    db.flush()
