from typing import Annotated

from fastapi import APIRouter, Depends, Path
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import require_roles
from app.modules.orders.schemas import OrderRead

from . import service
from .schemas import QuoteRead

router = APIRouter(
    prefix="/quotes", tags=["quotes"], dependencies=[Depends(require_roles("DIRECTOR", "SALES"))]
)
Db = Annotated[Session, Depends(get_db)]
QuoteId = Annotated[int, Path(gt=0, le=2_147_483_647)]


@router.get("/{quote_id}")
def quote_detail(quote_id: QuoteId, db: Db) -> dict[str, QuoteRead]:
    return {"data": QuoteRead.model_validate(service.get_quote(db, quote_id))}


@router.post("/{quote_id}/send")
def send_quote(quote_id: QuoteId, db: Db) -> dict[str, QuoteRead]:
    data = QuoteRead.model_validate(service.send(db, quote_id))
    db.commit()
    return {"data": data}


@router.post("/{quote_id}/accept")
def accept_quote(quote_id: QuoteId, db: Db) -> dict[str, OrderRead]:
    data = OrderRead.model_validate(service.accept(db, quote_id))
    db.commit()
    return {"data": data}
