"""Customer access projections. Every record query is scoped to explicit customer account ownership."""
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.modules.users.models import Customer
from app.modules.leads.models import Lead
from app.modules.surveys.models import Survey
from app.modules.quotes.models import Quote
from app.modules.orders.models import Order
from app.modules.deliveries.models import Delivery
from app.modules.installs.models import InstallJob
from app.modules.billing.models import Invoice
from app.modules.billing.service import get_invoice_detail
from app.modules.inventory.models import SerialUnit
from app.modules.catalog.models import Product
from app.modules.warranty.models import Warranty
from app.modules.tickets.models import Ticket
from app.modules.tickets.schemas import TicketCreate
from app.modules.tickets import service as tickets

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
    quotes = db.scalars(select(Quote).where(Quote.customer_id.in_(ids), Quote.status != "DRAFT").order_by(Quote.id.desc()).limit(50))
    invoices = db.scalars(select(Invoice).where(Invoice.customer_id.in_(ids), Invoice.status != "DRAFT").order_by(Invoice.id.desc()).limit(50))
    equipment = db.execute(select(SerialUnit, Product, Warranty).join(Product, SerialUnit.product_id == Product.id)
                           .outerjoin(Warranty, Warranty.serial_unit_id == SerialUnit.id)
                           .where(SerialUnit.customer_id.in_(ids)).order_by(SerialUnit.id.desc()).limit(100)).all()
    requests = db.scalars(select(Ticket).where(Ticket.customer_id.in_(ids)).order_by(Ticket.id.desc()).limit(50))
    return {
        "customer_id": customer_id,
        "projects": [{**fields(r, "id", "requested_kw", "status"),
                      "survey": fields(surveys[r.id], "scheduled_at", "status") if r.id in surveys else None} for r in leads],
        "orders": [{**fields(r, "id", "number", "status", "total_paise"),
                    "delivery": fields(deliveries[r.id], "status", "delivered_at") if r.id in deliveries else None,
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
    return {**fields(row, "id", "number", "status", "total_paise", "subtotal_paise", "subsidy_paise", "valid_until"),
            "customer": fields(customer, "name", "address"),
            "lines": [fields(line, "id", "description", "qty", "unit_price_paise", "line_paise") for line in row.lines]}


def request_service(db, customer_id, payload):
    serial = db.scalar(select(SerialUnit).where(SerialUnit.serial_no == payload.serial_no,
                                               SerialUnit.customer_id.in_(customer_ids(customer_id))))
    if serial is None:
        raise AppError("NOT_FOUND", "Select equipment belonging to your account.", 404)
    ticket = tickets.create(db, TicketCreate(serial_no=serial.serial_no, fault_code="CUSTOMER_REQUEST", description=payload.description))
    return fields(ticket, "id", "number", "status")
