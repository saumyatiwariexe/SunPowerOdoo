from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.core.deps import require_roles
from app.modules.billing import service
from app.modules.billing.schemas import InvoiceCreateIn, PaymentCreateIn

router = APIRouter(tags=["billing"])


@router.post("/orders/{order_id}/payments")
def post_order_payment(
    order_id: int,
    payload: PaymentCreateIn,
    db: Session = Depends(get_db),
    user=Depends(require_roles("SALES", "DIRECTOR")),
):
    data = service.record_payment(
        db=db,
        order_id=order_id,
        amount_paise=payload.amount_paise,
        method=payload.method,
        user_id=user.id,
        reference=payload.reference,
    )
    db.commit()
    return {"data": data}


@router.post("/invoices/{invoice_id}/payments")
def post_invoice_payment(
    invoice_id: int,
    payload: PaymentCreateIn,
    db: Session = Depends(get_db),
    user=Depends(require_roles("SALES", "DIRECTOR", "SUPPORT")),
):
    data = service.record_payment(
        db=db,
        invoice_id=invoice_id,
        amount_paise=payload.amount_paise,
        method=payload.method,
        user_id=user.id,
        reference=payload.reference,
    )
    db.commit()
    return {"data": data}


@router.get("/invoices")
def get_invoices(
    status: str | None = Query(default=None),
    db: Session = Depends(get_db),
    _user=Depends(require_roles("DIRECTOR", "SALES", "SUPPORT")),
):
    items = service.list_invoices(db, status=status)
    return {"data": items, "meta": {"total": len(items)}}


@router.post("/invoices")
def post_create_invoice(
    payload: InvoiceCreateIn,
    db: Session = Depends(get_db),
    _user=Depends(require_roles("DIRECTOR", "SALES")),
):
    data = service.create_order_invoice(db, payload.order_id)
    db.commit()
    return {"data": data}


@router.get("/invoices/{invoice_id}")
def get_invoice(
    invoice_id: int,
    db: Session = Depends(get_db),
    _user=Depends(require_roles("DIRECTOR", "SALES", "SUPPORT")),
):
    return {"data": service.get_invoice_detail(db, invoice_id)}