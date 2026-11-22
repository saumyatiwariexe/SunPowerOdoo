"""Customer access projections. Every record query is scoped to explicit customer account ownership."""
from datetime import UTC, datetime

from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.modules.users.models import Customer
from app.modules.leads.models import Lead
from app.modules.surveys.models import Survey
from app.modules.quotes.models import Quote
from app.modules.orders.models import Order
from app.modules.deliveries.models import Delivery
from app.modules.installs.models import InstallJob
from app.modules.billing.models import Invoice, Payment
from app.modules.billing.service import get_invoice_detail, get_order_paid_paise, record_payment
from app.modules.quotes.service import accept as accept_quote_service
from .models import CustomerPaymentReport
from app.modules.inventory.models import SerialUnit
from app.modules.catalog.models import Product
from app.modules.warranty.models import Warranty
from app.modules.tickets.models import Ticket
from app.modules.tickets.schemas import TicketCreate
from app.modules.tickets import service as tickets
from app.modules.subsidy.models import SubsidyClaim

COOKIE = "sunpower_customer"
COOKIE_PATH = "/api/v1/customer"


def customer_ids(customer_id):
    return select(Customer.id).where(Customer.id == customer_id)


def owned(db, model, record_id, customer_id):
    row = db.scalar(select(model).where(model.id == record_id, model.customer_id.in_(customer_ids(customer_id))))
    if row is None:
        raise AppError("NOT_FOUND", "Record not found.", 404)
    return row


def fields(row, *names):
    return {name: getattr(row, name) for name in names}


def overview(db: Session, customer_id: int):
    ids = customer_ids(customer_id)
    leads = list(db.scalars(select(Lead).where(Lead.customer_id.in_(ids)).order_by(Lead.id.desc()).limit(50)))
    orders = list(db.scalars(select(Order).where(Order.customer_id.in_(ids)).order_by(Order.id.desc()).limit(50)))
    surveys = {r.lead_id: r for r in db.scalars(select(Survey).where(Survey.lead_id.in_([r.id for r in leads])).order_by(Survey.id))}
    jobs = {r.order_id: r for r in db.scalars(select(InstallJob).where(InstallJob.order_id.in_([r.id for r in orders])))}
    deliveries = {r.order_id: r for r in db.scalars(select(Delivery).where(Delivery.order_id.in_([r.id for r in orders])))}
    order_invoices = {r.order_id: r for r in db.scalars(select(Invoice).where(Invoice.order_id.in_([r.id for r in orders])))}
    claims = {r.order_id: r for r in db.scalars(select(SubsidyClaim).where(SubsidyClaim.order_id.in_([r.id for r in orders])))}
    quotes = db.scalars(select(Quote).where(Quote.customer_id.in_(ids), Quote.status != "DRAFT").order_by(Quote.id.desc()).limit(50))
    invoices = db.scalars(select(Invoice).where(Invoice.customer_id.in_(ids), Invoice.status != "DRAFT").order_by(Invoice.id.desc()).limit(50))
    equipment = db.execute(select(SerialUnit, Product, Warranty).join(Product, SerialUnit.product_id == Product.id)
                           .outerjoin(Warranty, Warranty.serial_unit_id == SerialUnit.id)
                           .where(SerialUnit.customer_id.in_(ids)).order_by(SerialUnit.id.desc()).limit(100)).all()
    requests = db.scalars(select(Ticket).where(Ticket.customer_id.in_(ids)).order_by(Ticket.id.desc()).limit(50))
    paid = dict(db.execute(select(Payment.order_id, func.sum(Payment.amount_paise)).where(
        Payment.order_id.in_([r.id for r in orders])).group_by(Payment.order_id)).all())
    return {
        "customer_id": customer_id,
        "projects": [{**fields(r, "id", "requested_kw", "status"),
                      "survey": fields(surveys[r.id], "scheduled_at", "status") if r.id in surveys else None} for r in leads],
        "orders": [{**fields(r, "id", "number", "status", "total_paise", "advance_min_paise"),
                    "paid_paise": paid.get(r.id, 0),
                    "delivery": fields(deliveries[r.id], "status", "delivered_at") if r.id in deliveries else None,
                    "delivery_id": deliveries[r.id].id if r.id in deliveries else None,
                    "invoice_id": order_invoices[r.id].id if r.id in order_invoices else None,
                    "subsidy": fields(claims[r.id], "scheme", "status", "amount_paise", "reference_no") if r.id in claims else None,
                    "installation": fields(jobs[r.id], "status", "scheduled_start", "scheduled_end", "system_kw", "signed_by_name", "accepted_at") if r.id in jobs else None} for r in orders],
        "quotes": [fields(r, "id", "number", "status", "total_paise", "valid_until") for r in quotes],
        "invoices": [fields(r, "id", "number", "status", "total_paise", "paid_paise") for r in invoices],
        "equipment": [{"serial_no": s.serial_no, "product_name": p.name,
                       "warranty_start": w.start_date if w else None, "warranty_end": w.end_date if w else None,
                       "covered": bool(w and w.status == "ACTIVE" and w.start_date <= datetime.now(UTC).date() <= w.end_date)} for s, p, w in equipment],
        "tickets": [fields(r, "id", "number", "status", "description", "resolution", "billable") for r in requests],
    }


def document(db, kind, record_id, customer_id):
    row = owned(db, Quote if kind == "quotes" else Invoice, record_id, customer_id)
    if row.status == "DRAFT":
        raise AppError("NOT_FOUND", "Record not found.", 404)
    if kind == "invoices":
        return get_invoice_detail(db, row.id)
    customer = db.get(Customer, row.customer_id)
    order = db.scalar(select(Order).where(Order.quote_id == row.id))
    return {**fields(row, "id", "number", "status", "total_paise", "subtotal_paise", "subsidy_paise", "valid_until"),
            "order_id": order.id if order else None,
            "customer": fields(customer, "name", "address"),
            "lines": [fields(line, "id", "description", "qty", "unit_price_paise", "line_paise") for line in row.lines]}


def request_service(db, customer_id, payload):
    serial = db.scalar(select(SerialUnit).where(SerialUnit.serial_no == payload.serial_no,
                                               SerialUnit.customer_id.in_(customer_ids(customer_id))))
    if serial is None:
        raise AppError("NOT_FOUND", "Select equipment belonging to your account.", 404)
    ticket = tickets.create(db, TicketCreate(serial_no=serial.serial_no, fault_code="CUSTOMER_REQUEST", description=payload.description))
    return fields(ticket, "id", "number", "status")


def accept_quote(db, customer_id, quote_id):
    owned(db, Quote, quote_id, customer_id)
    order = accept_quote_service(db, quote_id)
    return fields(order, "id", "number", "status", "total_paise", "advance_min_paise")


def payment_target(db, kind, target_id, customer_id=None):
    model = Order if kind == "orders" else Invoice
    query = select(model).where(model.id == target_id)
    if customer_id is not None:
        query = query.where(model.customer_id == customer_id)
    row = db.scalar(query.execution_options(populate_existing=True))
    if row is None or (kind == "invoices" and row.status == "DRAFT"):
        raise AppError("NOT_FOUND", "Record not found.", 404)
    # Order-linked invoices use the same target as the advance to avoid double reporting.
    if kind == "invoices" and row.order_id is not None:
        return payment_target(db, "orders", row.order_id, customer_id)
    return db.scalar(query.with_for_update().execution_options(populate_existing=True))


def report_fields(row):
    return fields(row, "id", "amount_paise", "method", "reference", "status", "review_note", "created_at")


def payment_summary(db, kind, target_id, customer_id=None):
    row = payment_target(db, kind, target_id, customer_id)
    is_order = isinstance(row, Order)
    column = CustomerPaymentReport.order_id if is_order else CustomerPaymentReport.invoice_id
    reports = list(db.scalars(select(CustomerPaymentReport).where(column == row.id)
                             .order_by(CustomerPaymentReport.id.desc()).limit(50)))
    pending = db.scalar(select(func.sum(CustomerPaymentReport.amount_paise)).where(
        column == row.id, CustomerPaymentReport.status == "PENDING")) or 0
    paid = get_order_paid_paise(db, row.id) if is_order else row.paid_paise
    return {"number": row.number, "total_paise": row.total_paise, "paid_paise": paid,
            "advance_min_paise": row.advance_min_paise if is_order else None,
            "balance_paise": max(0, row.total_paise - paid), "pending_paise": pending,
            "reportable_paise": max(0, row.total_paise - paid - pending),
            "reports": [report_fields(r) for r in reports]}


def report_payment(db, customer_id, kind, target_id, payload):
    row = payment_target(db, kind, target_id, customer_id)
    summary = payment_summary(db, kind, target_id, customer_id)
    if payload.amount_paise > summary["reportable_paise"]:
        raise AppError("PAYMENT_EXCEEDS_BALANCE", "Amount exceeds the balance after pending reports.", 409)
    report = CustomerPaymentReport(customer_id=customer_id,
        order_id=row.id if isinstance(row, Order) else None,
        invoice_id=row.id if isinstance(row, Invoice) else None, **payload.model_dump())
    try:
        with db.begin_nested():
            db.add(report)
            db.flush()
    except IntegrityError as exc:
        raise AppError("PAYMENT_REFERENCE_EXISTS", "This transaction reference has already been reported.", 409) from exc
    return report_fields(report)


def review_payment(db, report_id, actor_id, payload):
    report = db.get(CustomerPaymentReport, report_id, with_for_update=True, populate_existing=True)
    if report is None:
        raise AppError("NOT_FOUND", "Payment report not found.", 404)
    if report.status == payload.decision:
        return report_fields(report)
    if report.status != "PENDING":
        raise AppError("PAYMENT_ALREADY_REVIEWED", "This payment report has already been reviewed.", 409)
    if payload.decision == "VERIFIED":
        kind, target_id = ("orders", report.order_id) if report.order_id else ("invoices", report.invoice_id)
        summary = payment_summary(db, kind, target_id)
        if report.amount_paise > summary["balance_paise"]:
            raise AppError("PAYMENT_EXCEEDS_BALANCE", "Payment exceeds the remaining balance. Check for an existing staff payment.", 409)
        duplicate = db.scalar(select(Payment.id).where(Payment.method == report.method,
                                                       func.upper(Payment.reference) == report.reference))
        if duplicate:
            raise AppError("PAYMENT_ALREADY_RECORDED", "This reference is already recorded. Reject the duplicate report.", 409)
        payment = record_payment(db, order_id=report.order_id, invoice_id=report.invoice_id,
            amount_paise=report.amount_paise, method=report.method, reference=report.reference, user_id=actor_id)
        report.payment_id = payment["payment_id"]
    report.status = payload.decision
    report.reviewed_by_id = actor_id
    report.review_note = payload.note
    db.flush()
    return report_fields(report)
