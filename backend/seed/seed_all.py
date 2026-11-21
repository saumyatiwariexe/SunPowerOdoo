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
from seed.seed_users import seed_users
from seed.seed_leads import seed_leads


def run_all() -> None:
    engine = get_engine()

    # Create all tables (safe to call repeatedly; skips existing tables)
    Base.metadata.create_all(engine)
    print("Tables created (or verified).")

    with Session(engine) as db:
        # 1. Seed number counters (QT, ORD, INV, TKT)
        seed_counters(db)
        db.commit()
        print("Counters seeded.")

        # 2. Seed demo users (one per role, password: sunpower123)
        seed_users(db, password="sunpower123")
        db.commit()
        print("Demo users seeded.")

        # 3. Seed leads + customers
        seed_leads(db)
        db.commit()
        print("Leads seeded.")

        # 4. Other module seeds — imported lazily so missing modules don't block startup
        _try_seed(db, "seed.seed_catalog", "seed_catalog")
        _try_seed(db, "seed.seed_inventory", "seed_inventory")
        _try_seed(db, "seed.seed_orders", "seed_orders")
        _try_seed(db, "seed.seed_deliveries", "seed_deliveries")
        _try_seed(db, "seed.seed_surveys", "seed_surveys")
        _try_seed(db, "seed.seed_installs", "seed_installs")
        _try_seed(db, "seed.seed_tickets", "seed_tickets")

    print("Seed complete.")


def _try_seed(db: Session, module_path: str, fn_name: str) -> None:
    try:
        import importlib

        mod = importlib.import_module(module_path)
        fn = getattr(mod, fn_name)
        fn(db)
        db.commit()
        print(f"{module_path}.{fn_name} → OK")
    except ModuleNotFoundError:
        print(f"{module_path} not found — skipping.")
    except Exception as exc:
        db.rollback()
        print(f"{module_path}.{fn_name} failed: {exc}")


if __name__ == "__main__":
    run_all()
