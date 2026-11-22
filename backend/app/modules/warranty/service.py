from datetime import datetime, timezone
from dateutil.relativedelta import relativedelta
from sqlalchemy import select, func, or_
from sqlalchemy.orm import Session
from app.core.errors import AppError
from app.modules.catalog.models import Product
from app.modules.deliveries.models import Delivery, DeliveryScan
from app.modules.inventory.models import SerialUnit
from app.modules.orders.models import Order
from app.modules.users.models import Customer
from app.modules.warranty.models import Warranty


def start_for_delivery(db: Session, delivery_id: int) -> list[Warranty]:
    """Contract R8: creates one warranty per scanned serial unit on the delivery."""
    delivery = db.scalar(select(Delivery).where(Delivery.id == delivery_id))
    if not delivery:
        raise AppError("NOT_FOUND", "Delivery not found", 404)

    order = db.scalar(select(Order).where(Order.id == delivery.order_id))
    if not order:
        raise AppError("NOT_FOUND", "Order not found", 404)

    if delivery.status != "DELIVERED" or delivery.delivered_at is None:
        raise AppError("DELIVERY_NOT_COMPLETED", "Complete the delivery before starting warranties.", 409)
    start_dt = delivery.delivered_at.date()
    scans = db.scalars(select(DeliveryScan).where(DeliveryScan.delivery_id == delivery.id)).all()

    created: list[Warranty] = []
    for sc in scans:
        existing = db.scalar(select(Warranty).where(Warranty.serial_unit_id == sc.serial_unit_id))
        if existing:
            created.append(existing)
            continue

        su = db.scalar(select(SerialUnit).where(SerialUnit.id == sc.serial_unit_id))
        if not su:
            continue
        prod = db.scalar(select(Product).where(Product.id == su.product_id))
        months = prod.warranty_months if (prod and prod.warranty_months) else 0
        if months <= 0:
            raise AppError("WARRANTY_DURATION_REQUIRED", f"Set warranty months for serial {su.serial_no}.", 409)

        end_dt = start_dt + relativedelta(months=months)
        status = "ACTIVE" if datetime.now(timezone.utc).date() <= end_dt else "EXPIRED"

        w = Warranty(
            serial_unit_id=su.id,
            customer_id=order.customer_id,
            order_id=order.id,
            start_date=start_dt,
            end_date=end_dt,
            status=status,
        )
        db.add(w)
        created.append(w)

    db.flush()
    return created


def check_by_serial(db: Session, serial_no: str) -> dict:
    """Contract R9: computes real-time in_warranty status from end_date."""
    clean_sn = serial_no.strip()
    su = db.scalar(select(SerialUnit).where(func.lower(SerialUnit.serial_no) == clean_sn.lower()))
    if not su:
        raise AppError("NOT_FOUND", f"Serial number '{clean_sn}' not found", 404)

    prod = db.scalar(select(Product).where(Product.id == su.product_id))
    customer = db.scalar(select(Customer).where(Customer.id == su.customer_id)) if su.customer_id else None
    warranty = db.scalar(select(Warranty).where(Warranty.serial_unit_id == su.id))

    today = datetime.now(timezone.utc).date()
    in_warranty = False
    warranty_status = "NO_WARRANTY"

    if warranty:
        if warranty.status == "VOID":
            warranty_status = "VOID"
            in_warranty = False
        elif warranty.start_date <= today <= warranty.end_date and warranty.status == "ACTIVE":
            warranty_status = "ACTIVE"
            in_warranty = True
        else:
            warranty_status = "EXPIRED"
            in_warranty = False

    return {
        "serial_unit_id": su.id,
        "serial_no": su.serial_no,
        "product_id": su.product_id,
        "product_name": prod.name if prod else "",
        "sku": prod.sku if prod else "",
        "installed_at": su.installed_at,
        "customer_id": customer.id if customer else None,
        "customer_name": customer.name if customer else None,
        "customer_phone": customer.phone if customer else None,
        "warranty_id": warranty.id if warranty else None,
        "start_date": warranty.start_date if warranty else None,
        "end_date": warranty.end_date if warranty else None,
        "in_warranty": in_warranty,
        "warranty_status": warranty_status,
    }


def check_by_phone(db: Session, phone: str) -> list[dict]:
    serial_numbers = db.scalars(
        select(SerialUnit.serial_no).join(Customer, Customer.id == SerialUnit.customer_id)
        .where(func.replace(func.replace(func.replace(Customer.phone, " ", ""), "-", ""), "+", "").in_(("".join(c for c in phone if c.isdigit())[-10:], "91" + "".join(c for c in phone if c.isdigit())[-10:]))).order_by(SerialUnit.serial_no)
    ).all()
    return [check_by_serial(db, serial_no) for serial_no in serial_numbers]


def search_equipment(db: Session, q: str, assigned_only: bool = False) -> list[dict]:
    query = select(SerialUnit, Product, Customer, Warranty).join(Product, Product.id == SerialUnit.product_id).outerjoin(Customer, Customer.id == SerialUnit.customer_id).outerjoin(Warranty, Warranty.serial_unit_id == SerialUnit.id)
    term = q.strip()
    if term:
        query = query.where(or_(SerialUnit.serial_no.icontains(term, autoescape=True), Customer.name.icontains(term, autoescape=True), Customer.phone.icontains(term, autoescape=True)))
    if assigned_only:
        query = query.where(SerialUnit.customer_id.is_not(None))
    rows = db.execute(query.order_by(SerialUnit.id.desc()).limit(30)).all()
    today = datetime.now(timezone.utc).date()
    return [{"serial_no": s.serial_no, "product_name": p.name, "customer_id": c.id if c else None,
             "customer_name": c.name if c else "Warehouse stock", "customer_phone": c.phone if c else None,
             "end_date": w.end_date if w else None,
             "warranty_status": "ACTIVE" if w and w.status == "ACTIVE" and w.start_date <= today <= w.end_date else w.status if w and w.status == "VOID" else "EXPIRED" if w else "NO_WARRANTY"}
            for s,p,c,w in rows]
