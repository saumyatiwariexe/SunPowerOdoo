from typing import Annotated

from fastapi import APIRouter, Depends, Path
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import require_roles

from . import service
from .schemas import OrderRead

router = APIRouter(
    prefix="/orders", tags=["orders"], dependencies=[Depends(require_roles("DIRECTOR", "SALES"))]
)
OrderId = Annotated[int, Path(gt=0, le=2_147_483_647)]
Db = Annotated[Session, Depends(get_db)]


@router.get("/{order_id}")
def order_detail(
    order_id: OrderId, db: Db,
) -> dict[str, OrderRead]:
    return {"data": OrderRead.model_validate(service.get_order(db, order_id))}


@router.post("/{order_id}/confirm")
def confirm_order(order_id: OrderId, db: Db) -> dict[str, OrderRead]:
    data = OrderRead.model_validate(service.confirm(db, order_id))
    db.commit()
    return {"data": data}
