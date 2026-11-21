from datetime import date, datetime, timezone
from dateutil.relativedelta import relativedelta
from sqlalchemy import select
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

    start_dt = (delivery.delivered_at or datetime.now(timezone.utc)).date()
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
            continue

        end_dt = start_dt + relativedelta(months=months)
        status = "ACTIVE" if date.today() <= end_dt else "EXPIRED"

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
    su = db.scalar(select(SerialUnit).where(SerialUnit.serial_no == clean_sn))
    if not su:
        raise AppError("NOT_FOUND", f"Serial number '{clean_sn}' not found", 404)

    prod = db.scalar(select(Product).where(Product.id == su.product_id))
    customer = db.scalar(select(Customer).where(Customer.id == su.customer_id)) if su.customer_id else None
    warranty = db.scalar(select(Warranty).where(Warranty.serial_unit_id == su.id))

    today = date.today()
    in_warranty = False
    warranty_status = "NO_WARRANTY"

    if warranty:
        if warranty.status == "VOID":
            warranty_status = "VOID"
            in_warranty = False
        elif today <= warranty.end_date and warranty.status == "ACTIVE":
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