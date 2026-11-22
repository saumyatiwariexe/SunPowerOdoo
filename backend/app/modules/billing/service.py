from datetime import datetime, timezone
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from app.core.errors import AppError
from app.core.pagination import Pagination
from app.core.numbering import next_number
from app.modules.billing.models import Invoice, InvoiceLine, Payment
from app.modules.orders.models import Order
from app.modules.quotes.models import Quote, QuoteLine
from app.modules.tickets.models import Ticket, TicketLine
from app.modules.users.models import Customer

MAX_PAISE = 9_223_372_036_854_775_807


def _sync_invoice_payment_status(invoice: Invoice) -> None:
    if invoice.total_paise <= 0 or invoice.paid_paise >= invoice.total_paise:
        invoice.status = "PAID"
    elif invoice.paid_paise > 0:
        invoice.status = "PARTIAL"
    else:
        invoice.status = "SENT"


def get_order_paid_paise(db: Session, order_id: int) -> int:
    total = db.scalar(select(func.sum(Payment.amount_paise)).where(Payment.order_id == order_id))
    return int(total or 0)


def record_payment(
    db: Session,
    order_id: int | None = None,
    amount_paise: int = 0,
    method: str = "UPI",
    user_id: int = 1,
    reference: str | None = None,
    invoice_id: int | None = None,
) -> dict:
    """Contract called by router for order advance/balance payments or invoice payments."""
    if type(amount_paise) is not int or not 0 < amount_paise <= MAX_PAISE:
        raise AppError("RULE_VIOLATION", "Payment amount must be greater than zero", 409)

    if order_id is None and invoice_id is None:
        raise AppError("VALIDATION_ERROR", "Either order_id or invoice_id is required", 400)

    target_order = None
    target_invoice = None
    if invoice_id is not None:
        invoice = db.get(Invoice, invoice_id)
        if invoice is None:
            raise AppError("NOT_FOUND", "Invoice not found", 404)
        if order_id is not None and invoice.order_id != order_id:
            raise AppError("PAYMENT_TARGET_MISMATCH", "The invoice does not belong to the order.", 409)
        order_id = invoice.order_id

    if order_id is not None:
        target_order = db.get(Order, order_id, with_for_update=True, populate_existing=True)
        if not target_order:
            raise AppError("NOT_FOUND", "Order not found", 404)

    if invoice_id is not None:
        target_invoice = db.get(Invoice, invoice_id, with_for_update=True, populate_existing=True)
    elif target_order is not None:
        query = select(Invoice).where(Invoice.order_id == target_order.id).with_for_update()
        target_invoice = db.scalar(query.execution_options(populate_existing=True))

    total_order_paid = get_order_paid_paise(db, target_order.id) if target_order is not None else 0
    invoice_paid = target_invoice.paid_paise if target_invoice is not None else 0
    if max(total_order_paid, invoice_paid) + amount_paise > MAX_PAISE:
        raise AppError("PAYMENT_TOTAL_TOO_LARGE", "The paid total exceeds the supported range.", 409)

    payment = Payment(
        order_id=target_order.id if target_order else None,
        invoice_id=target_invoice.id if target_invoice else None,
        amount_paise=amount_paise,
        method=method,
        reference=reference,
        paid_at=datetime.now(timezone.utc),
        received_by_id=user_id,
    )
    db.add(payment)
    db.flush()

    if target_invoice:
        target_invoice.paid_paise += amount_paise
        _sync_invoice_payment_status(target_invoice)

    db.flush()
    return {
        "payment_id": payment.id,
        "order_id": payment.order_id,
        "invoice_id": payment.invoice_id,
        "amount_paise": payment.amount_paise,
        "method": payment.method,
        "reference": payment.reference,
        "paid_at": payment.paid_at,
        "total_order_paid_paise": total_order_paid + amount_paise if target_order is not None else 0,
    }


def create_order_invoice(db: Session, order_id: int) -> dict:
    order = db.get(Order, order_id, with_for_update=True, populate_existing=True)
    if not order:
        raise AppError("NOT_FOUND", "Order not found", 404)
    existing = db.scalar(select(Invoice).where(Invoice.order_id == order_id))
    if existing:
        return get_invoice_detail(db, existing.id)

    quote = db.scalar(select(Quote).where(Quote.id == order.quote_id))
    quote_lines = db.scalars(select(QuoteLine).where(QuoteLine.quote_id == order.quote_id)).all()

    already_paid = get_order_paid_paise(db, order.id)

    inv_number = next_number(db, "INV")
    invoice = Invoice(
        number=inv_number,
        order_id=order.id,
        customer_id=order.customer_id,
        status="SENT",
        total_paise=order.total_paise,
        paid_paise=already_paid,
        issued_at=datetime.now(timezone.utc),
    )
    _sync_invoice_payment_status(invoice)
    db.add(invoice)
    db.flush()

    for ql in quote_lines:
        db.add(
            InvoiceLine(
                invoice_id=invoice.id,
                description=ql.description,
                qty=ql.qty,
                unit_price_paise=ql.unit_price_paise,
            )
        )

    if quote and quote.subsidy_paise > 0:
        db.add(
            InvoiceLine(
                invoice_id=invoice.id,
                description="Government Rooftop Solar Subsidy Credit",
                qty=1,
                unit_price_paise=-quote.subsidy_paise,
            )
        )

    # Link prior order payments to this invoice
    prior_payments = db.scalars(select(Payment).where(Payment.order_id == order.id)).all()
    for p in prior_payments:
        p.invoice_id = invoice.id

    db.flush()
    return get_invoice_detail(db, invoice.id)


def create_ticket_invoice(db: Session, ticket_id: int) -> Invoice | None:
    """Contract R10: called by tickets.close. Returns None if in-warranty (no charge)."""
    existing = db.scalar(select(Invoice).where(Invoice.ticket_id == ticket_id))
    if existing:
        return existing

    ticket = db.scalar(select(Ticket).where(Ticket.id == ticket_id))
    if not ticket:
        raise AppError("NOT_FOUND", "Ticket not found", 404)

    if not ticket.billable:
        return None

    lines = db.scalars(select(TicketLine).where(TicketLine.ticket_id == ticket.id)).all()
    total_paise = sum(ln.qty * ln.unit_price_paise for ln in lines)
    if total_paise <= 0:
        return None

    inv_number = next_number(db, "INV")
    invoice = Invoice(
        number=inv_number,
        ticket_id=ticket.id,
        customer_id=ticket.customer_id,
        status="SENT",
        total_paise=total_paise,
        paid_paise=0,
        issued_at=datetime.now(timezone.utc),
    )
    db.add(invoice)
    db.flush()

    for ln in lines:
        db.add(
            InvoiceLine(
                invoice_id=invoice.id,
                description=ln.description,
                qty=ln.qty,
                unit_price_paise=ln.unit_price_paise,
            )
        )

    db.flush()
    return invoice


def list_invoices(db: Session, paging: Pagination, status: str | None = None) -> tuple[list[dict], int]:
    stmt = select(Invoice, Customer.name).join(Customer, Customer.id == Invoice.customer_id)
    if status:
        stmt = stmt.where(Invoice.status == status)
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    invoices = db.execute(stmt.order_by(Invoice.id.desc())
                          .offset(paging.offset).limit(paging.page_size))

    out = []
    for inv, customer_name in invoices:
        out.append({
            "id": inv.id,
            "number": inv.number,
            "order_id": inv.order_id,
            "ticket_id": inv.ticket_id,
            "customer_id": inv.customer_id,
            "customer_name": customer_name,
            "status": inv.status,
            "total_paise": inv.total_paise,
            "paid_paise": inv.paid_paise,
            "balance_paise": max(0, inv.total_paise - inv.paid_paise),
            "issued_at": inv.issued_at,
        })
    return out, total


def get_invoice_detail(db: Session, invoice_id: int) -> dict:
    inv = db.scalar(select(Invoice).where(Invoice.id == invoice_id))
    if not inv:
        raise AppError("NOT_FOUND", "Invoice not found", 404)

    cust = db.scalar(select(Customer).where(Customer.id == inv.customer_id))
    lines = db.scalars(select(InvoiceLine).where(InvoiceLine.invoice_id == inv.id)).all()
    payments = db.scalars(select(Payment).where(Payment.invoice_id == inv.id)).all()

    return {
        "id": inv.id,
        "number": inv.number,
        "order_id": inv.order_id,
        "ticket_id": inv.ticket_id,
        "customer": {
            "id": cust.id,
            "name": cust.name,
            "phone": cust.phone,
            "email": cust.email,
            "address": cust.address,
            "city": cust.city,
            "pincode": cust.pincode,
        } if cust else None,
        "status": inv.status,
        "total_paise": inv.total_paise,
        "paid_paise": inv.paid_paise,
        "balance_paise": max(0, inv.total_paise - inv.paid_paise),
        "issued_at": inv.issued_at,
        "lines": [
            {
                "id": ln.id,
                "description": ln.description,
                "qty": ln.qty,
                "unit_price_paise": ln.unit_price_paise,
                "line_paise": ln.qty * ln.unit_price_paise,
            }
            for ln in lines
        ],
        "payments": [
            {
                "id": p.id,
                "amount_paise": p.amount_paise,
                "method": p.method,
                "reference": p.reference,
                "paid_at": p.paid_at,
            }
            for p in payments
        ],
    }
