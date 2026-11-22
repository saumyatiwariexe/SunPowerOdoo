from sqlalchemy import cast, func, select, String
from sqlalchemy.orm import Session, selectinload

from app.core.errors import AppError
from app.modules.leads.models import Lead, LeadCall, LeadSource, LeadStatus, LEAD_TRANSITIONS
from app.modules.leads.schemas import LeadCallCreate, LeadCreate, LeadLostIn, LeadUpdate, NewCustomerLead
from app.modules.users.models import Customer, User


def _get_or_404(db: Session, lead_id: int) -> Lead:
    lead = db.get(Lead, lead_id)
    if lead is None:
        raise AppError("LEAD_NOT_FOUND", f"Lead {lead_id} not found.", 404)
    return lead


def list_leads(
    db: Session,
    *,
    page: int = 1,
    page_size: int = 20,
    q: str | None = None,
    status: str | None = None,
) -> tuple[list[Lead], int]:
    stmt = select(Lead).options(selectinload(Lead.customer))
    if status:
        try:
            s = LeadStatus(status)
        except ValueError:
            raise AppError("INVALID_STATUS", f"Unknown lead status: {status}", 400)
        stmt = stmt.where(Lead.status == s)
    if q:
        # Join customers to filter by name or phone
        stmt = (
            stmt.join(Customer, Customer.id == Lead.customer_id)
            .where(Customer.name.ilike(f"%{q}%") | Customer.phone.ilike(f"%{q}%"))
        )
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    rows = db.scalars(stmt.order_by(Lead.id.desc()).offset((page - 1) * page_size).limit(page_size)).all()
    return list(rows), total or 0


def get_lead(db: Session, lead_id: int) -> Lead:
    return _get_or_404(db, lead_id)


def create_lead(db: Session, data: LeadCreate | NewCustomerLead, actor: User) -> Lead:
    if isinstance(data, NewCustomerLead):
        customer = Customer(name=data.name, phone=data.phone, address=data.address, pincode=data.pincode)
        db.add(customer)
        db.flush()
    else:
        customer = db.get(Customer, data.customer_id)
        if customer is None:
            raise AppError("CUSTOMER_NOT_FOUND", "Customer not found.", 404)
    lead = Lead(
        customer_id=customer.id,
        source=data.source,
        requested_kw=data.requested_kw,
        system_type=data.system_type,
        subsidy_interest=data.subsidy_interest,
        assigned_to_id=data.assigned_to_id,
        notes=data.notes,
        status=LeadStatus.NEW,
    )
    db.add(lead)
    db.flush()
    return lead


def update_lead(db: Session, lead_id: int, data: LeadUpdate, actor: User) -> Lead:
    lead = _get_or_404(db, lead_id)
    updates = data.model_dump(exclude_unset=True)

    if "status" in updates:
        new_status = LeadStatus(updates["status"])
        if new_status not in LEAD_TRANSITIONS.get(lead.status, set()):
            raise AppError(
                "INVALID_TRANSITION",
                f"Cannot move lead from {lead.status} to {new_status}.",
                409,
            )
        if new_status == LeadStatus.LOST and not updates.get("lost_reason") and not lead.lost_reason:
            raise AppError("LOST_REASON_REQUIRED", "Provide a lost_reason when marking a lead LOST (R1).", 409)

    for field, value in updates.items():
        setattr(lead, field, value)
    db.flush()
    return lead


def mark_lost(db: Session, lead_id: int, data: LeadLostIn, actor: User) -> Lead:
    """R1: Mark lead as LOST. lost_reason is mandatory. Leads are never deleted."""
    lead = _get_or_404(db, lead_id)
    if lead.status == LeadStatus.LOST:
        raise AppError("ALREADY_LOST", "Lead is already marked as LOST.", 409)
    if lead.status == LeadStatus.WON:
        raise AppError("LEAD_WON", "Cannot mark a WON lead as LOST.", 409)
    lead.status = LeadStatus.LOST
    lead.lost_reason = data.lost_reason
    db.flush()
    return lead


def add_call(db: Session, lead_id: int, data: LeadCallCreate, actor: User) -> LeadCall:
    lead = _get_or_404(db, lead_id)
    if lead.status == LeadStatus.LOST:
        raise AppError("LEAD_LOST", "Cannot log a call on a LOST lead.", 409)
    call = LeadCall(
        lead_id=lead_id,
        called_by_id=actor.id,
        shadow_free_area_sqm=data.shadow_free_area_sqm,
        monthly_bill_paise=data.monthly_bill_paise,
        grid_suitable=data.grid_suitable,
        outcome=data.outcome,
        notes=data.notes,
        called_at=data.called_at,
    )
    db.add(call)
    # Auto-advance status NEW -> CONTACTED on first call
    if lead.status == LeadStatus.NEW:
        lead.status = LeadStatus.CONTACTED
    db.flush()
    return call


def request_survey(db: Session, lead_id: int, actor: User) -> Lead:
    """Advance lead to SURVEY_PENDING."""
    lead = _get_or_404(db, lead_id)
    if LeadStatus.SURVEY_PENDING not in LEAD_TRANSITIONS.get(lead.status, set()):
        raise AppError(
            "INVALID_TRANSITION",
            f"Cannot request survey from status {lead.status}. Lead must be in CONTACTED state.",
            409,
        )
    lead.status = LeadStatus.SURVEY_PENDING
    db.flush()
    return lead
