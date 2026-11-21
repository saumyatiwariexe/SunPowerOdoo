from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import AppError
from app.core.money import minimum_advance_paise
from app.core.numbering import NumberPrefix, next_number
from app.modules.billing.service import get_order_paid_paise

from .models import Order, OrderStatus


def get_order(db: Session, order_id: int, *, for_update: bool = False) -> Order:
    order = db.get(Order, order_id, with_for_update=for_update, populate_existing=for_update)
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


def confirm(db: Session, order_id: int) -> Order:
    """Apply R4 and R5 in the caller's transaction."""
    # Billing takes the same order lock when it records a payment.
    order = get_order(db, order_id, for_update=True)
    if order.status == OrderStatus.CONFIRMED:
        return order
    if order.status != OrderStatus.DRAFT:
        raise AppError("ORDER_NOT_DRAFT", "Only a draft order can be confirmed.", 409)

    if order.advance_min_paise > 0:
        paid_paise = get_order_paid_paise(db, order_id)
        if paid_paise < order.advance_min_paise:
            remaining = order.advance_min_paise - paid_paise
            raise AppError("ADVANCE_REQUIRED", f"Record {remaining} more paise to confirm this order.", 409)

    from app.modules.deliveries.service import create_for_order as create_delivery
    from app.modules.installs.service import create_for_order

    order.status = OrderStatus.CONFIRMED
    order.confirmed_at = datetime.now(UTC)
    db.flush()
    create_delivery(db, order.id)
    create_for_order(db, order.id)
    return order


def mark_installed(db: Session, order_id: int) -> Order:
    order = get_order(db, order_id, for_update=True)
    if order.status != OrderStatus.DISPATCHED:
        raise AppError("ORDER_NOT_DISPATCHED", "Dispatch the order before accepting installation.", 409)
    order.status = OrderStatus.INSTALLED
    db.flush()
    return order


def mark_dispatched(db: Session, order_id: int) -> Order:
    order = get_order(db, order_id, for_update=True)
    if order.status != OrderStatus.CONFIRMED:
        raise AppError("ORDER_NOT_CONFIRMED", "Confirm the order before dispatching it.", 409)
    order.status = OrderStatus.DISPATCHED
    db.flush()
    return order
