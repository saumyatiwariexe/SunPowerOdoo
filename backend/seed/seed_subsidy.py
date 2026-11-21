from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.leads.models import Lead
from app.modules.orders.models import Order, OrderStatus
from app.modules.quotes.models import Quote
from app.modules.subsidy.models import SubsidyClaim, claim_order_index
from app.modules.subsidy.service import create_for_interested_order


def backfill_subsidy_claims(db: Session) -> None:
    # create_all skips new indexes on existing tables.
    claim_order_index.create(db.connection(), checkfirst=True)
    has_claim = select(SubsidyClaim.id).where(SubsidyClaim.order_id == Order.id).exists()
    eligible = (
        select(Order)
        .join(Quote, Quote.id == Order.quote_id)
        .join(Lead, Lead.id == Quote.lead_id)
        .where(Order.status.not_in((OrderStatus.DRAFT, OrderStatus.CANCELLED)),
               Lead.subsidy_interest.is_(True), ~has_claim)
        .order_by(Order.id)
        .with_for_update(of=Order)
    )
    for order in db.scalars(eligible):
        create_for_interested_order(db, order)
