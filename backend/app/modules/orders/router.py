from typing import Annotated

from fastapi import APIRouter, Depends, Path
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import require_roles
from app.core.pagination import Pagination
from app.modules.billing.service import get_order_paid_paise
from app.modules.billing.models import Invoice
from app.modules.deliveries.models import Delivery
from app.modules.subsidy.models import SubsidyClaim
from app.modules.users.models import Customer
from sqlalchemy import select

from . import service
from .schemas import OrderDetailRead, OrderPage, OrderRead
from .models import OrderStatus

router = APIRouter(
    prefix="/orders", tags=["orders"], dependencies=[Depends(require_roles("DIRECTOR", "SALES"))]
)
OrderId = Annotated[int, Path(gt=0, le=2_147_483_647)]
Db = Annotated[Session, Depends(get_db)]


@router.get("")
def order_list(db: Db, paging: Annotated[Pagination, Depends()]) -> OrderPage:
    rows, count = service.list_orders(db, paging)
    return OrderPage(data=[OrderRead.model_validate(row) for row in rows], meta=paging.meta(count))


@router.get("/options")
def options(db: Db, paging: Annotated[Pagination, Depends()], status: OrderStatus | None = None) -> dict:
    rows, count = service.order_options(db, paging, status=status)
    return {"data": rows, "meta": paging.meta(count)}


@router.get("/{order_id}")
def order_detail(
    order_id: OrderId, db: Db,
) -> dict[str, OrderDetailRead]:
    order = OrderRead.model_validate(service.get_order(db, order_id))
    return {"data": OrderDetailRead(**order.model_dump(), paid_paise=get_order_paid_paise(db, order_id))}


@router.get("/{order_id}/connections")
def order_connections(order_id: OrderId, db: Db):
    order = service.get_order(db, order_id)
    customer = db.get(Customer, order.customer_id)
    return {"data": {"customer_name": customer.name if customer else None,
        "delivery_id": db.scalar(select(Delivery.id).where(Delivery.order_id == order_id)),
        "invoice_id": db.scalar(select(Invoice.id).where(Invoice.order_id == order_id)),
        "subsidy_claim_id": db.scalar(select(SubsidyClaim.id).where(SubsidyClaim.order_id == order_id))}}


@router.post("/{order_id}/confirm")
def confirm_order(order_id: OrderId, db: Db) -> dict[str, OrderRead]:
    data = OrderRead.model_validate(service.confirm(db, order_id))
    db.commit()
    return {"data": data}
