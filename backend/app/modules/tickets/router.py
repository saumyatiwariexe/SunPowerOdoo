from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import require_roles
from app.core.pagination import Pagination

from . import service
from .models import TicketStatus
from .schemas import TicketClosure, TicketCreate, TicketLineCreate, TicketLineRead, TicketPage, TicketPatch, TicketRead, TicketResolve

router = APIRouter(
    prefix="/tickets", tags=["tickets"], dependencies=[Depends(require_roles("SUPPORT", "DIRECTOR"))]
)
Db = Annotated[Session, Depends(get_db)]
TicketId = Annotated[int, Path(gt=0, le=2_147_483_647)]


@router.get("")
def tickets(
    db: Db,
    paging: Annotated[Pagination, Depends()],
    q: Annotated[str, Query(max_length=100)] = "",
    status: TicketStatus | None = None,
    assigned_to_id: Annotated[int | None, Query(gt=0, le=2_147_483_647)] = None,
) -> TicketPage:
    rows, count = service.list_tickets(db, paging, q, status, assigned_to_id)
    return TicketPage(data=[TicketRead.model_validate(row) for row in rows], meta=paging.meta(count))


@router.post("", status_code=201)
def create(payload: TicketCreate, db: Db) -> dict[str, TicketRead]:
    data = TicketRead.model_validate(service.create(db, payload))
    db.commit()
    return {"data": data}


@router.get("/{ticket_id}")
def detail(ticket_id: TicketId, db: Db) -> dict[str, TicketRead]:
    return {"data": TicketRead.model_validate(service.get_ticket(db, ticket_id))}


@router.patch("/{ticket_id}")
def update(ticket_id: TicketId, payload: TicketPatch, db: Db) -> dict[str, TicketRead]:
    data = TicketRead.model_validate(service.update(db, ticket_id, payload))
    db.commit()
    return {"data": data}


@router.post("/{ticket_id}/lines", status_code=201)
def add_line(ticket_id: TicketId, payload: TicketLineCreate, db: Db) -> dict[str, TicketLineRead]:
    data = TicketLineRead.model_validate(service.add_line(db, ticket_id, payload))
    db.commit()
    return {"data": data}


@router.post("/{ticket_id}/resolve")
def resolve(ticket_id: TicketId, payload: TicketResolve, db: Db) -> dict[str, TicketRead]:
    data = TicketRead.model_validate(service.resolve(db, ticket_id, payload.resolution))
    db.commit()
    return {"data": data}


@router.post("/{ticket_id}/confirm")
def confirm_customer(ticket_id: TicketId, db: Db) -> dict[str, TicketRead]:
    data = TicketRead.model_validate(service.confirm_customer(db, ticket_id))
    db.commit()
    return {"data": data}


@router.post("/{ticket_id}/close")
def close(ticket_id: TicketId, db: Db) -> dict[str, TicketClosure]:
    ticket, invoice_id = service.close(db, ticket_id)
    data = TicketClosure(ticket=TicketRead.model_validate(ticket), invoice_id=invoice_id)
    db.commit()
    return {"data": data}
