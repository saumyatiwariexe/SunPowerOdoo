"""Add customer portal accounts without changing or seeding existing data."""
import app.models_registry  # noqa: F401
from app.core.db import get_engine
from app.modules.portal.models import CustomerAccount

if __name__ == "__main__":
    CustomerAccount.__table__.create(get_engine(), checkfirst=True)
    print("Customer account table is ready; existing records were preserved.")
