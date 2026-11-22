"""Add the payment-report table without modifying or seeding existing data.

Run from backend: python -m app.modules.portal.upgrade_payments
"""
import app.models_registry  # noqa: F401
from app.core.db import get_engine
from .models import CustomerPaymentReport


if __name__ == "__main__":
    CustomerPaymentReport.__table__.create(get_engine(), checkfirst=True)
    print("Customer payment-report table is ready. Existing data preserved.")
