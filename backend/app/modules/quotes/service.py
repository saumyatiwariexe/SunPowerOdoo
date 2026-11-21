from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.modules.orders.models import Order
from app.modules.orders.service import create_for_quote

from .models import Quote, QuoteStatus


def get_quote(db: Session, quote_id: int, *, for_update: bool = False) -> Quote:
    quote = db.get(Quote, quote_id, with_for_update=for_update, populate_existing=for_update)
    if quote is None:
        raise AppError("QUOTE_NOT_FOUND", "Quote not found.", 404)
    return quote


def _require_unexpired(quote: Quote) -> None:
    if quote.valid_until < datetime.now(UTC).date():
        raise AppError("QUOTE_EXPIRED", "The quote validity date has passed.", 409)


def send(db: Session, quote_id: int) -> Quote:
    quote = get_quote(db, quote_id, for_update=True)
    if quote.status != QuoteStatus.DRAFT:
        raise AppError("QUOTE_NOT_DRAFT", "Only a draft quote can be sent.", 409)
    _require_unexpired(quote)
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
        _require_unexpired(quote)
        quote.status = QuoteStatus.ACCEPTED
        db.flush()
    elif quote.status != QuoteStatus.ACCEPTED:
        raise AppError("QUOTE_NOT_SENT", "Send the quote before accepting it.", 409)

    return _convert_accepted_quote(db, quote)
