"""
seed_all.py — master seed script.
Run from backend/ directory:
    python -m seed.seed_all

Creates all tables via SQLAlchemy create_all, then seeds users, leads, and other
modules' seed functions as they become available.
"""
import sys
from pathlib import Path

# Ensure backend/ is on the path when run as a script
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy.orm import Session

import app.models_registry  # noqa: F401 — registers all ORM models with Base
from app.core.db import Base, get_engine
from app.core.numbering import seed_counters
from seed.seed_b import seed_historical_delivery
from seed.seed_catalog import seed_catalog
from seed.seed_inventory import seed_inventory
from seed.seed_surveys import seed_surveys
from seed.seed_users import seed_users
from seed.seed_leads import seed_leads
from seed.seed_subsidy import backfill_subsidy_claims


def run_all() -> None:
    engine = get_engine()

    # Create all tables (safe to call repeatedly; skips existing tables)
    Base.metadata.create_all(engine)
    print("Tables created (or verified).")

    with Session(engine) as db, db.begin():
        seed_counters(db)
        seed_users(db, password="sunpower123")
        seed_leads(db)
        seed_catalog(db)
        seed_inventory(db)
        seed_historical_delivery(db)
        seed_surveys(db)
        backfill_subsidy_claims(db)
    print("Seed complete.")


if __name__ == "__main__":
    run_all()
