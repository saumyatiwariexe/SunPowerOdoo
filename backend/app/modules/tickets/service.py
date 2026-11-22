from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.errors import AppError
from app.core.deps import has_role
from app.core.numbering import NumberPrefix, next_number
from app.core.pagination import Pagination
from app.modules.billing import service as billing
from app.modules.catalog.service import get_product
from app.modules.inventory.models import SerialUnit
from app.modules.users.models import Role, User, Customer
from app.modules.warranty.service import check_by_serial

from .models import Ticket, TicketLine, TicketStatus
from .schemas import MAX_PAISE, TicketCreate, TicketLineCreate, TicketPatch


def get_ticket(db: Session, ticket_id: int, *, for_update: bool = False) -> Ticket:
    ticket = db.get(Ticket, ticket_id, with_for_update=for_update, populate_existing=for_update)
    if ticket is None:
        raise AppError("TICKET_NOT_FOUND", "Ticket not found.", 404)
    describe_tickets(db, [ticket])
    return ticket


def list_tickets(
    db: Session, paging: Pagination, q: str, status: TicketStatus | None, assigned_to_id: int | None
) -> tuple[list[Ticket], int]:
    filters = []
    if q:
        filters.append(Ticket.number.icontains(q, autoescape=True) | Ticket.description.icontains(q, autoescape=True) | Ticket.customer_id.in_(select(Customer.id).where(Customer.name.icontains(q, autoescape=True))) | Ticket.serial_unit_id.in_(select(SerialUnit.id).where(SerialUnit.serial_no.icontains(q, autoescape=True))))
    if status is not None:
        filters.append(Ticket.status == status)
    if assigned_to_id is not None:
        filters.append(Ticket.assigned_to_id == assigned_to_id)
    total = db.scalar(select(func.count()).select_from(Ticket).where(*filters)) or 0
    query = (
        select(Ticket).where(*filters).options(selectinload(Ticket.lines))
        .order_by(Ticket.id.desc()).offset(paging.offset).limit(paging.page_size)
    )
    rows = list(db.scalars(query))
    describe_tickets(db, rows)
    return rows, total


def create(db: Session, payload: TicketCreate) -> Ticket:
    coverage = check_by_serial(db, payload.serial_no)
    if coverage["customer_id"] is None:
        raise AppError("SERIAL_NOT_ASSIGNED", "The serial number has no customer yet.", 409)
    ticket = Ticket(
        number=next_number(db, NumberPrefix.TICKET),
        customer_id=coverage["customer_id"],
        serial_unit_id=coverage["serial_unit_id"],
        warranty_id=coverage["warranty_id"],
        fault_code=payload.fault_code,
        description=payload.description,
        priority=payload.priority,
        billable=not coverage["in_warranty"],
    )
    db.add(ticket)
    db.flush()
    if payload.assigned_to_id is not None:
        update(db, ticket.id, TicketPatch(assigned_to_id=payload.assigned_to_id))
    describe_tickets(db, [ticket])
    return ticket


def update(db: Session, ticket_id: int, payload: TicketPatch) -> Ticket:
    ticket = get_ticket(db, ticket_id, for_update=True)
    if ticket.status == TicketStatus.CLOSED:
        raise AppError("TICKET_CLOSED", "A closed ticket cannot be edited.", 409)
    changes = payload.model_dump(exclude_unset=True)
    if {"description", "fault_code"} & changes.keys() and ticket.status == TicketStatus.RESOLVED:
        raise AppError("TICKET_RESOLVED", "Issue details cannot change after resolution.", 409)
    if "status" in changes and ticket.status != TicketStatus.OPEN:
        raise AppError("TICKET_NOT_OPEN", "Only an open ticket can move to in progress.", 409)
    assignee_id = changes.get("assigned_to_id")
    if assignee_id is not None:
        assignee = db.get(User, assignee_id)
        if assignee is None or not assignee.active or not any(has_role(assignee, role) for role in (Role.CREW, Role.SUPPORT, Role.DIRECTOR)):
            raise AppError("INVALID_TICKET_ASSIGNEE", "Assign an active crew, support or director user.", 409)
    for field, value in changes.items():
        setattr(ticket, field, value)
    db.flush()
    describe_tickets(db, [ticket])
    return ticket


def add_line(db: Session, ticket_id: int, payload: TicketLineCreate) -> TicketLine:
    ticket = get_ticket(db, ticket_id, for_update=True)
    if ticket.status == TicketStatus.CLOSED:
        raise AppError("TICKET_LINES_LOCKED", "A closed ticket cannot be edited.", 409)
    if payload.product_id is not None:
        get_product(db, payload.product_id)
    total = payload.qty * payload.unit_price_paise
    total += sum(line.qty * line.unit_price_paise for line in ticket.lines)
    if total > MAX_PAISE:
        raise AppError("TICKET_TOTAL_TOO_LARGE", "The ticket total exceeds the supported range.", 409)
    line = TicketLine(**payload.model_dump())
    ticket.lines.append(line)
    ticket.customer_confirmed_at = None
    db.flush()
    return line


def resolve(db: Session, ticket_id: int, resolution: str) -> Ticket:
    ticket = get_ticket(db, ticket_id, for_update=True)
    if ticket.status != TicketStatus.IN_PROGRESS:
        raise AppError("TICKET_NOT_IN_PROGRESS", "Start work before resolving the ticket.", 409)
    ticket.resolution = resolution
    ticket.status = TicketStatus.RESOLVED
    db.flush()
    return ticket


def confirm_customer(db: Session, ticket_id: int) -> Ticket:
    ticket = get_ticket(db, ticket_id, for_update=True)
    if ticket.status != TicketStatus.RESOLVED:
        raise AppError("TICKET_NOT_RESOLVED", "Resolve the ticket before recording confirmation.", 409)
    if ticket.customer_confirmed_at is None:
        ticket.customer_confirmed_at = datetime.now(UTC)
        db.flush()
    return ticket


def close(db: Session, ticket_id: int) -> tuple[Ticket, int | None]:
    ticket = get_ticket(db, ticket_id, for_update=True)
    if ticket.status == TicketStatus.CLOSED:
        invoice = billing.create_ticket_invoice(db, ticket.id) if ticket.billable else None
        return ticket, invoice.id if invoice is not None else None
    if ticket.status != TicketStatus.RESOLVED or ticket.customer_confirmed_at is None:
        raise AppError("CUSTOMER_CONFIRMATION_REQUIRED", "Record customer confirmation before closing.", 409)

    serial = db.get(SerialUnit, ticket.serial_unit_id)
    coverage = check_by_serial(db, serial.serial_no)
    ticket.warranty_id = coverage["warranty_id"]
    ticket.billable = not coverage["in_warranty"]
    invoice = billing.create_ticket_invoice(db, ticket.id) if ticket.billable else None
    if ticket.billable and invoice is None:
        raise AppError("BILLABLE_LINES_REQUIRED", "Record chargeable parts or labour before closing.", 409)
    ticket.status = TicketStatus.CLOSED
    db.flush()
    return ticket, invoice.id if invoice is not None else None


def describe_tickets(db, rows):
    customers = {c.id:c for c in db.scalars(select(Customer).where(Customer.id.in_([r.customer_id for r in rows])))}
    serials = {s.id:s.serial_no for s in db.scalars(select(SerialUnit).where(SerialUnit.id.in_([r.serial_unit_id for r in rows])))}
    users = {u.id:u.name for u in db.scalars(select(User).where(User.id.in_([r.assigned_to_id for r in rows if r.assigned_to_id])))}
    for row in rows:
        customer = customers.get(row.customer_id)
        row.customer_name = customer.name if customer else None
        row.customer_phone = customer.phone if customer else None
        row.serial_no = serials.get(row.serial_unit_id)
        row.assigned_to_name = users.get(row.assigned_to_id)
