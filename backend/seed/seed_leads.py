"""
seed_leads.py — creates demo leads in various states plus a demo customer.
"""
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.leads.models import Lead, LeadCall, LeadSource, LeadStatus, SystemType
from app.modules.users.models import Customer, User, Role


def seed_leads(db: Session) -> None:
    # Idempotent: skip if any leads already exist
    if db.scalar(select(Lead)):
        return

    sales_user = db.scalar(select(User).where(User.email == "sales@sunpower.test"))
    director_user = db.scalar(select(User).where(User.email == "director@sunpower.test"))

    # --- Customer 1: active lead going through the funnel ---
    customer1 = Customer(
        name="Ramesh Kumar",
        phone="9876543210",
        email="ramesh@example.com",
        address="12 MG Road, Sector 5",
        city="Bengaluru",
        pincode="560001",
    )
    db.add(customer1)
    db.flush()

    lead1 = Lead(
        customer_id=customer1.id,
        source=LeadSource.WEB,
        requested_kw=3.0,
        system_type=SystemType.ON_GRID,
        subsidy_interest=True,
        status=LeadStatus.CONTACTED,
        assigned_to_id=sales_user.id if sales_user else None,
        notes="Interested in 3 kW on-grid with subsidy.",
    )
    db.add(lead1)
    db.flush()

    db.add(
        LeadCall(
            lead_id=lead1.id,
            called_by_id=sales_user.id if sales_user else (director_user.id if director_user else 1),
            shadow_free_area_sqm=25.0,
            monthly_bill_paise=350000,
            grid_suitable=True,
            outcome="Interested, wants a site visit.",
            called_at=datetime.now(UTC) - timedelta(days=1),
        )
    )

    # --- Customer 2: lost lead (R1 demo) ---
    customer2 = Customer(
        name="Sunita Sharma",
        phone="9123456780",
        email="sunita@example.com",
        address="88 Park Street",
        city="Mumbai",
        pincode="400001",
    )
    db.add(customer2)
    db.flush()

    lead2 = Lead(
        customer_id=customer2.id,
        source=LeadSource.WHATSAPP,
        requested_kw=5.0,
        system_type=SystemType.OFF_GRID,
        subsidy_interest=False,
        status=LeadStatus.LOST,
        assigned_to_id=sales_user.id if sales_user else None,
        lost_reason="Customer decided to buy from a competitor.",
    )
    db.add(lead2)

    # --- Customer 3: Survey pending ---
    customer3 = Customer(
        name="Ajay Mehta",
        phone="9000012345",
        email="ajay@example.com",
        address="5 Residency Road",
        city="Hyderabad",
        pincode="500001",
    )
    db.add(customer3)
    db.flush()

    lead3 = Lead(
        customer_id=customer3.id,
        source=LeadSource.CALL,
        requested_kw=2.0,
        system_type=SystemType.ON_GRID,
        subsidy_interest=True,
        status=LeadStatus.SURVEY_PENDING,
        assigned_to_id=sales_user.id if sales_user else None,
        notes="Roof available. Survey requested.",
    )
    db.add(lead3)

    # --- Customer 4: New lead from web enquiry ---
    customer4 = Customer(
        name="Priya Nair",
        phone="8812345678",
        email="priya@example.com",
        address="22 Beach Road",
        city="Kochi",
        pincode="682001",
    )
    db.add(customer4)
    db.flush()

    lead4 = Lead(
        customer_id=customer4.id,
        source=LeadSource.WEB,
        requested_kw=1.0,
        system_type=SystemType.ON_GRID,
        subsidy_interest=True,
        status=LeadStatus.NEW,
    )
    db.add(lead4)

    db.flush()
