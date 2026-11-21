from datetime import UTC, date, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.errors import AppError
from app.core.numbering import NumberPrefix, next_number
from app.core.pagination import Pagination
from app.modules.catalog.service import get_package, get_package_bom
from app.modules.leads import service as leads
from app.modules.leads.models import LeadStatus
from app.modules.leads.schemas import LeadUpdate
from app.modules.orders.models import Order
from app.modules.orders.service import create_for_quote
from app.modules.surveys.service import is_approved
from app.modules.users.models import User

from .models import Quote, QuoteLine, QuoteStatus
from .schemas import MAX_PAISE, QuoteCreate, QuotePatch


def get_quote(db: Session, quote_id: int, *, for_update: bool = False) -> Quote:
    quote = db.get(Quote, quote_id, with_for_update=for_update, populate_existing=for_update)
    if quote is None:
        raise AppError("QUOTE_NOT_FOUND", "Quote not found.", 404)
    return quote


def _require_unexpired(valid_until: date) -> None:
    if valid_until < datetime.now(UTC).date():
        raise AppError("QUOTE_EXPIRED", "The quote validity date has passed.", 409)


def list_quotes(
    db: Session, paging: Pagination, q: str, status: QuoteStatus | None
) -> tuple[list[Quote], int]:
    filters = []
    if q:
        filters.append(Quote.number.icontains(q, autoescape=True))
    if status is not None:
        filters.append(Quote.status == status)
    count = db.scalar(select(func.count()).select_from(Quote).where(*filters)) or 0
    statement = (
        select(Quote)
        .where(*filters)
        .options(selectinload(Quote.lines))
        .order_by(Quote.id.desc())
        .offset(paging.offset)
        .limit(paging.page_size)
    )
    return list(db.scalars(statement)), count


def _reprice(quote: Quote, subsidy_paise: int) -> None:
    subtotal = 0
    for line in quote.lines:
        line.line_paise = line.qty * line.unit_price_paise
        subtotal += line.line_paise
    if subtotal > MAX_PAISE:
        raise AppError("QUOTE_TOTAL_TOO_LARGE", "The quote subtotal exceeds the supported range.", 409)
    if subsidy_paise > subtotal:
        raise AppError("SUBSIDY_EXCEEDS_SUBTOTAL", "The subsidy cannot exceed the quote subtotal.", 409)
    quote.subtotal_paise = subtotal
    quote.subsidy_paise = subsidy_paise
    quote.total_paise = subtotal - subsidy_paise


def create_from_package(db: Session, payload: QuoteCreate, actor: User) -> Quote:
    _require_unexpired(payload.valid_until)
    lead = leads.get_lead(db, payload.lead_id)
    db.refresh(lead, with_for_update=True)
    if not is_approved(db, lead.id):
        raise AppError("SURVEY_NOT_APPROVED", "Approve the lead's survey before creating a quote.", 409)
    if lead.status not in {LeadStatus.SURVEY_PENDING, LeadStatus.SURVEY_DONE, LeadStatus.QUOTED}:
        raise AppError("LEAD_NOT_QUOTABLE", "The lead is not ready for a quote.", 409)

    package = get_package(db, payload.package_id, for_update=True)
    if not package.active:
        raise AppError("PACKAGE_INACTIVE", "Select an active package.", 409)
    parts = get_package_bom(db, package.id)
    if not parts:
        raise AppError("PACKAGE_BOM_EMPTY", "Add products to the package before quoting it.", 409)

    quote = Quote(
        lead_id=lead.id,
        customer_id=lead.customer_id,
        package_id=package.id,
        valid_until=payload.valid_until,
        lines=[
            QuoteLine(
                product_id=item.product_id,
                description=item.product.name,
                qty=item.qty,
                unit_price_paise=item.product.price_paise,
            )
            for item in parts
        ],
    )
    _reprice(quote, payload.subsidy_paise)
    quote.number = next_number(db, NumberPrefix.QUOTE)
    if lead.status == LeadStatus.SURVEY_PENDING:
        leads.update_lead(db, lead.id, LeadUpdate(status=LeadStatus.SURVEY_DONE), actor)
    if lead.status == LeadStatus.SURVEY_DONE:
        leads.update_lead(db, lead.id, LeadUpdate(status=LeadStatus.QUOTED), actor)
    db.add(quote)
    db.flush()
    return quote


def update_draft(db: Session, quote_id: int, payload: QuotePatch) -> Quote:
    quote = get_quote(db, quote_id, for_update=True)
    if quote.status != QuoteStatus.DRAFT:
        raise AppError("QUOTE_NOT_DRAFT", "Only a draft quote can be edited.", 409)
    if payload.valid_until is not None:
        _require_unexpired(payload.valid_until)
        quote.valid_until = payload.valid_until
    if payload.lines:
        lines = {line.id: line for line in quote.lines}
        for change in payload.lines:
            if change.id not in lines:
                raise AppError("INVALID_QUOTE_LINE", "The quote does not contain that line.", 409)
            line = lines[change.id]
            line.qty = change.qty
            line.unit_price_paise = change.unit_price_paise
    subsidy = quote.subsidy_paise if payload.subsidy_paise is None else payload.subsidy_paise
    _reprice(quote, subsidy)
    db.flush()
    return quote


def send(db: Session, quote_id: int) -> Quote:
    quote = get_quote(db, quote_id, for_update=True)
    if quote.status != QuoteStatus.DRAFT:
        raise AppError("QUOTE_NOT_DRAFT", "Only a draft quote can be sent.", 409)
    _require_unexpired(quote.valid_until)
    quote.status = QuoteStatus.SENT
    db.flush()
    return quote


def _convert_accepted_quote(db: Session, quote: Quote) -> Order:
    if quote.status != QuoteStatus.ACCEPTED:
        raise AppError("QUOTE_NOT_ACCEPTED", "Accept the quote before creating an order.", 409)
    return create_for_quote(
        db, quote_id=quote.id, customer_id=quote.customer_id, total_paise=quote.total_paise
    )


def convert_to_order(db: Session, quote_id: int) -> Order:
    """Return the one draft order created from the accepted quote."""
    quote = get_quote(db, quote_id, for_update=True)
    return _convert_accepted_quote(db, quote)


def accept(db: Session, quote_id: int) -> Order:
    quote = get_quote(db, quote_id, for_update=True)
    if quote.status == QuoteStatus.SENT:
        _require_unexpired(quote.valid_until)
        quote.status = QuoteStatus.ACCEPTED
        db.flush()
    elif quote.status != QuoteStatus.ACCEPTED:
        raise AppError("QUOTE_NOT_SENT", "Send the quote before accepting it.", 409)

    return _convert_accepted_quote(db, quote)
