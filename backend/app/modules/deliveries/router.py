from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.core.deps import require_roles
from app.modules.deliveries import service
from app.modules.deliveries.schemas import DispatchIn, ScanSerialIn

router = APIRouter(prefix="/deliveries", tags=["deliveries"])


@router.get("")
def get_deliveries(
    status: str | None = Query(default=None),
    db: Session = Depends(get_db),
    _user=Depends(require_roles("WAREHOUSE", "DIRECTOR", "CREW")),
):
    items = service.list_deliveries(db, status=status)
    return {"data": items, "meta": {"total": len(items)}}


@router.get("/{delivery_id}")
def get_delivery(
    delivery_id: int,
    db: Session = Depends(get_db),
    _user=Depends(require_roles("WAREHOUSE", "DIRECTOR", "CREW")),
):
    return {"data": service.get_delivery_detail(db, delivery_id)}


@router.post("/{delivery_id}/scan")
def post_scan_serial(
    delivery_id: int,
    payload: ScanSerialIn,
    db: Session = Depends(get_db),
    user=Depends(require_roles("WAREHOUSE", "DIRECTOR")),
):
    data = service.scan_serial(db, delivery_id, payload.serial_no, user.id)
    db.commit()
    return {"data": data}


@router.delete("/{delivery_id}/scan/{serial_unit_id}")
def delete_scan_serial(
    delivery_id: int,
    serial_unit_id: int,
    db: Session = Depends(get_db),
    _user=Depends(require_roles("WAREHOUSE", "DIRECTOR")),
):
    data = service.unscan_serial(db, delivery_id, serial_unit_id)
    db.commit()
    return {"data": data}


@router.post("/{delivery_id}/dispatch")
def post_dispatch_delivery(
    delivery_id: int,
    payload: DispatchIn | None = None,
    db: Session = Depends(get_db),
    _user=Depends(require_roles("WAREHOUSE", "DIRECTOR")),
):
    vehicle = payload.vehicle if payload else None
    data = service.dispatch(db, delivery_id, vehicle=vehicle)
    db.commit()
    return {"data": data}


@router.post("/{delivery_id}/deliver")
def post_deliver_delivery(
    delivery_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_roles("WAREHOUSE", "DIRECTOR", "CREW")),
):
    data = service.complete(db, delivery_id, delivered_by_id=user.id)
    db.commit()
    return {"data": data}