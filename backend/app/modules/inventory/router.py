from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.core.pagination import Pagination
from app.core.deps import require_roles
from app.modules.inventory import service
from app.modules.inventory.schemas import StockReceiveIn

router = APIRouter(tags=["inventory"])


@router.get("/stock")
def get_products_stock(
    q: str | None = Query(default=None),
    low_stock: bool = Query(default=False),
    paging: Pagination = Depends(),
    db: Session = Depends(get_db),
    _user=Depends(require_roles("WAREHOUSE", "DIRECTOR", "SALES", "SUPPORT")),
):
    items, total = service.list_stock(db, paging, q=q, low_stock_only=low_stock)
    return {"data": items, "meta": paging.meta(total)}


@router.post("/stock/receive")
def post_receive_stock(
    payload: StockReceiveIn,
    db: Session = Depends(get_db),
    _user=Depends(require_roles("WAREHOUSE", "DIRECTOR")),
):
    res = service.receive_stock(db, payload)
    db.commit()
    return {"data": res}
