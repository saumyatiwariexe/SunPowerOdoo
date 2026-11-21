from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import AppError
from app.core.money import minimum_advance_paise
from app.core.numbering import NumberPrefix, next_number

from .models import Order


def get_order(db: Session, order_id: int) -> Order:
    order = db.get(Order, order_id)
    if order is None:
        raise AppError("ORDER_NOT_FOUND", "Order not found.", 404)
    return order


def create_for_quote(db: Session, *, quote_id: int, customer_id: int, total_paise: int) -> Order:
    """Create a draft order while the caller holds the accepted quote's row lock."""
    order = db.scalar(select(Order).where(Order.quote_id == quote_id))
    if order is not None:
        return order

    advance = minimum_advance_paise(total_paise, get_settings().advance_percent)
    order = Order(
        number=next_number(db, NumberPrefix.ORDER),
        quote_id=quote_id,
        customer_id=customer_id,
        total_paise=total_paise,
        advance_min_paise=advance,
    )
    db.add(order)
    db.flush()
    return order
