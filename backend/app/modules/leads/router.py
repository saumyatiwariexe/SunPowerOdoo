from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import require_roles
from app.core.pagination import Pagination
from app.modules.leads import service
from app.modules.leads.schemas import LeadCallCreate, LeadCallOut, LeadCreate, LeadDetail, LeadLostIn, LeadOut, LeadUpdate, NewCustomerLead, SalesLeadSummary
from app.modules.users.models import Role, User

router = APIRouter(prefix="/leads", tags=["leads"])

AnyStaff = require_roles(Role.DIRECTOR, Role.SALES, Role.SURVEYOR, Role.SUPPORT)
SalesOrDirector = require_roles(Role.DIRECTOR, Role.SALES)


@router.get("", response_model=dict)
def list_leads(
    db: Annotated[Session, Depends(get_db)],
    actor: Annotated[User, Depends(AnyStaff)],
    pg: Annotated[Pagination, Depends()],
    q: str | None = None,
    status: str | None = None,
) -> dict:
    rows, total = service.list_leads(db, page=pg.page, page_size=pg.page_size, q=q, status=status)
    schema = SalesLeadSummary if actor.role in {Role.SALES, Role.DIRECTOR} else LeadOut
    return {"data": [schema.model_validate(r) for r in rows], "meta": pg.meta(total)}


@router.post("", response_model=dict, status_code=201)
def create_lead(
    body: LeadCreate | NewCustomerLead,
    db: Annotated[Session, Depends(get_db)],
    actor: Annotated[User, Depends(SalesOrDirector)],
) -> dict:
    lead = service.create_lead(db, body, actor)
    db.commit()
    db.refresh(lead)
    return {"data": LeadOut.model_validate(lead)}


@router.get("/{lead_id}", response_model=dict)
def get_lead(
    lead_id: int,
    db: Annotated[Session, Depends(get_db)],
    actor: Annotated[User, Depends(AnyStaff)],
) -> dict:
    lead = service.get_lead(db, lead_id)
    schema = LeadDetail if actor.role in {Role.SALES, Role.DIRECTOR} else LeadOut
    return {"data": schema.model_validate(lead)}


@router.patch("/{lead_id}", response_model=dict)
def update_lead(
    lead_id: int,
    body: LeadUpdate,
    db: Annotated[Session, Depends(get_db)],
    actor: Annotated[User, Depends(SalesOrDirector)],
) -> dict:
    lead = service.update_lead(db, lead_id, body, actor)
    db.commit()
    db.refresh(lead)
    return {"data": LeadOut.model_validate(lead)}


@router.post("/{lead_id}/lost", response_model=dict)
def mark_lost(
    lead_id: int,
    body: LeadLostIn,
    db: Annotated[Session, Depends(get_db)],
    actor: Annotated[User, Depends(SalesOrDirector)],
) -> dict:
    lead = service.mark_lost(db, lead_id, body, actor)
    db.commit()
    db.refresh(lead)
    return {"data": LeadOut.model_validate(lead)}


@router.post("/{lead_id}/calls", response_model=dict, status_code=201)
def add_call(
    lead_id: int,
    body: LeadCallCreate,
    db: Annotated[Session, Depends(get_db)],
    actor: Annotated[User, Depends(SalesOrDirector)],
) -> dict:
    call = service.add_call(db, lead_id, body, actor)
    db.commit()
    db.refresh(call)
    return {"data": LeadCallOut.model_validate(call)}


@router.post("/{lead_id}/survey-request", response_model=dict)
def request_survey(
    lead_id: int,
    db: Annotated[Session, Depends(get_db)],
    actor: Annotated[User, Depends(SalesOrDirector)],
) -> dict:
    lead = service.request_survey(db, lead_id, actor)
    db.commit()
    db.refresh(lead)
    return {"data": LeadOut.model_validate(lead)}
