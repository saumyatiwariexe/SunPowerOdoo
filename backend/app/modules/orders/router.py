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


@router.get("/{order_id}")
def order_detail(
    order_id: Annotated[int, Path(gt=0, le=2_147_483_647)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, OrderRead]:
    return {"data": OrderRead.model_validate(service.get_order(db, order_id))}
