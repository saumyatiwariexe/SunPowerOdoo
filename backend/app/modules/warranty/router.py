from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.core.deps import require_roles
from app.modules.warranty import service

router = APIRouter(tags=["warranty"])


@router.get("/lookup")
def lookup_serial(
    serial: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
    _user=Depends(require_roles("SUPPORT", "DIRECTOR", "CREW", "WAREHOUSE")),
):
    data = service.check_by_serial(db, serial)
    return {"data": data}