from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.modules.leads.models import Lead
from app.modules.orders.models import Order
from app.modules.quotes.models import Quote
from app.modules.subsidy.models import SubsidyClaim, SubsidyStatus
from app.modules.subsidy.schemas import SubsidyClaimUpdate


def create_for_interested_order(db: Session, order: Order) -> None:
    """Called while holding the order lock, including during legacy backfill."""
    amount = db.scalar(
        select(Quote.subsidy_paise).join(Lead, Lead.id == Quote.lead_id)
        .where(Quote.id == order.quote_id, Lead.subsidy_interest.is_(True))
    )
    if amount is None or db.scalar(select(SubsidyClaim.id).where(SubsidyClaim.order_id == order.id)):
        return
    db.add(SubsidyClaim(order_id=order.id, amount_paise=amount, scheme="Scheme pending"))
    db.flush()


def _get_or_404(db: Session, claim_id: int) -> SubsidyClaim:
    claim = db.get(SubsidyClaim, claim_id)
    if claim is None:
        raise AppError("CLAIM_NOT_FOUND", f"SubsidyClaim {claim_id} not found.", 404)
    return claim


def list_claims(
    db: Session,
    *,
    page: int = 1,
    page_size: int = 20,
    status: str | None = None,
) -> tuple[list[SubsidyClaim], int]:
    from sqlalchemy import func

    stmt = select(SubsidyClaim)
    if status:
        try:
            s = SubsidyStatus(status)
        except ValueError:
            raise AppError("INVALID_STATUS", f"Unknown subsidy status: {status}", 400)
        stmt = stmt.where(SubsidyClaim.status == s)
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    rows = db.scalars(
        stmt.order_by(SubsidyClaim.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return list(rows), total or 0


def get_claim(db: Session, claim_id: int) -> SubsidyClaim:
    return _get_or_404(db, claim_id)


def update_claim(db: Session, claim_id: int, data: SubsidyClaimUpdate) -> SubsidyClaim:
    claim = _get_or_404(db, claim_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(claim, field, value)
    db.flush()
    return claim
