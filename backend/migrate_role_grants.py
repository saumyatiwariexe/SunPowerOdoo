"""Add the role grant table to an existing database without touching its data."""

import app.models_registry  # noqa: F401

from app.core.db import get_engine
from app.modules.users.models import UserRoleGrant


if __name__ == "__main__":
    UserRoleGrant.__table__.create(get_engine(), checkfirst=True)
    print("Role grant table is ready.")
