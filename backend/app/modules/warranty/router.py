from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.core.deps import require_roles
from app.core.errors import AppError
from app.modules.warranty import service

router = APIRouter(tags=["warranty"])


@router.get("/lookup")
def lookup_serial(
    serial: str | None = Query(default=None, min_length=1, max_length=100),
    phone: str | None = Query(default=None, min_length=1, max_length=20),
    db: Session = Depends(get_db),
    _user=Depends(require_roles("SUPPORT", "DIRECTOR", "CREW", "WAREHOUSE")),
):
    if bool(serial and serial.strip()) == bool(phone and phone.strip()):
        raise AppError("LOOKUP_QUERY_REQUIRED", "Enter either a serial number or a phone number.", 400)
    if serial is not None and serial.strip():
        return {"data": service.check_by_serial(db, serial)}
    return {"data": service.check_by_phone(db, phone)}
