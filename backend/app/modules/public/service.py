from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.modules.leads.models import Lead, LeadSource, LeadStatus, SystemType
from app.modules.public.schemas import EnquiryIn, EnquiryOut
from app.modules.users.models import Customer


def create_enquiry(db: Session, data: EnquiryIn) -> EnquiryOut:
    """
    Public enquiry submission.
    Dedup rule: if the same phone submitted within 10 minutes, attach to the same lead.
    """
    # Honeypot already validated by Pydantic (website field must be empty)

    ten_min_ago = datetime.now(UTC) - timedelta(minutes=10)

    # Check for recent duplicate phone
    recent_customer = db.scalar(
        select(Customer).where(Customer.phone == data.phone).order_by(Customer.created_at.desc())
    )
    existing_lead: Lead | None = None
    if recent_customer:
        existing_lead = db.scalar(
            select(Lead)
            .where(
                Lead.customer_id == recent_customer.id,
                Lead.created_at >= ten_min_ago,
            )
            .order_by(Lead.created_at.desc())
        )

    if existing_lead:
        return EnquiryOut(
            lead_id=existing_lead.id,
            customer_id=existing_lead.customer_id,
            reference=f"LEAD-{existing_lead.id:04d}",
        )

    # Create customer
    customer = Customer(
        name=data.name,
        phone=data.phone,
        email=data.email,
        address=data.address,
        city=data.city,
        pincode=data.pincode,
    )
    db.add(customer)
    db.flush()

    # Create lead
    lead = Lead(
        customer_id=customer.id,
        source=LeadSource.WEB,
        requested_kw=data.requested_kw,
        system_type=SystemType(data.system_type),
        subsidy_interest=data.subsidy_interest,
        status=LeadStatus.NEW,
    )
    db.add(lead)
    db.flush()

    return EnquiryOut(
        lead_id=lead.id,
        customer_id=customer.id,
        reference=f"LEAD-{lead.id:04d}",
    )


def get_packages_public(db: Session) -> list:
    """Return active packages for the public landing page. Gracefully handles missing table."""
    try:
        from app.modules.catalog.models import Package  # type: ignore

        packages = db.scalars(
            select(Package).where(Package.active.is_(True)).order_by(Package.capacity_kw)
        ).all()
        return list(packages)
    except Exception:
        return []
