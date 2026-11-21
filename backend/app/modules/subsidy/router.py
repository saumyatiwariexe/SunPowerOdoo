from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import require_roles
from app.core.pagination import Pagination
from app.modules.subsidy import service
from app.modules.subsidy.schemas import SubsidyClaimOut, SubsidyClaimUpdate
from app.modules.users.models import Role, User

router = APIRouter(prefix="/subsidy", tags=["subsidy"])

DirectorOrSales = require_roles(Role.DIRECTOR, Role.SALES)


@router.get("", response_model=dict)
def list_claims(
    db: Annotated[Session, Depends(get_db)],
    actor: Annotated[User, Depends(DirectorOrSales)],
    pg: Annotated[Pagination, Depends()],
    status: str | None = None,
) -> dict:
    rows, total = service.list_claims(db, page=pg.page, page_size=pg.page_size, status=status)
    return {"data": [SubsidyClaimOut.model_validate(r) for r in rows], "meta": pg.meta(total)}


@router.get("/{claim_id}", response_model=dict)
def get_claim(
    claim_id: int,
    db: Annotated[Session, Depends(get_db)],
    actor: Annotated[User, Depends(DirectorOrSales)],
) -> dict:
    claim = service.get_claim(db, claim_id)
    return {"data": SubsidyClaimOut.model_validate(claim)}


@router.patch("/{claim_id}", response_model=dict)
def update_claim(
    claim_id: int,
    body: SubsidyClaimUpdate,
    db: Annotated[Session, Depends(get_db)],
    actor: Annotated[User, Depends(DirectorOrSales)],
) -> dict:
    claim = service.update_claim(db, claim_id, body)
    db.commit()
    db.refresh(claim)
    return {"data": SubsidyClaimOut.model_validate(claim)}
