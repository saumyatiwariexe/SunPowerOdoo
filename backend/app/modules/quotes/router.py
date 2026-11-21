from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import require_roles
from app.core.pagination import Pagination
from app.modules.orders.schemas import OrderRead
from app.modules.users.models import User

from . import service
from .models import QuoteStatus
from .schemas import QuoteCreate, QuotePage, QuotePatch, QuoteRead

quote_staff = require_roles("DIRECTOR", "SALES")
router = APIRouter(
    prefix="/quotes", tags=["quotes"], dependencies=[Depends(quote_staff)]
)
Db = Annotated[Session, Depends(get_db)]
QuoteId = Annotated[int, Path(gt=0, le=2_147_483_647)]


@router.get("")
def quotes(
    db: Db,
    paging: Annotated[Pagination, Depends()],
    q: Annotated[str, Query(max_length=24)] = "",
    status: QuoteStatus | None = None,
) -> QuotePage:
    rows, count = service.list_quotes(db, paging, q, status)
    return QuotePage(data=[QuoteRead.model_validate(row) for row in rows], meta=paging.meta(count))


@router.post("", status_code=201)
def create_quote(
    payload: QuoteCreate, db: Db, actor: Annotated[User, Depends(quote_staff)]
) -> dict[str, QuoteRead]:
    quote = QuoteRead.model_validate(service.create_from_package(db, payload, actor))
    db.commit()
    return {"data": quote}


@router.get("/{quote_id}")
def quote_detail(quote_id: QuoteId, db: Db) -> dict[str, QuoteRead]:
    return {"data": QuoteRead.model_validate(service.get_quote(db, quote_id))}


@router.patch("/{quote_id}")
def edit_quote(quote_id: QuoteId, payload: QuotePatch, db: Db) -> dict[str, QuoteRead]:
    quote = QuoteRead.model_validate(service.update_draft(db, quote_id, payload))
    db.commit()
    return {"data": quote}


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
