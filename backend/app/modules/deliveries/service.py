from datetime import datetime, timezone
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from app.core.errors import AppError
from app.modules.catalog.models import Product
from app.modules.catalog.service import adjust_stock
from app.modules.deliveries.models import Delivery, DeliveryLine, DeliveryScan
from app.modules.inventory.models import SerialUnit, StockMovement
from app.modules.orders.models import Order
from app.modules.orders.service import mark_dispatched
from app.modules.quotes.models import QuoteLine
from app.modules.warranty import service as warranty_service


def create_for_order(db: Session, order_id: int) -> Delivery:
    """Contract called by orders.service.confirm inside the same transaction."""
    existing = db.scalar(select(Delivery).where(Delivery.order_id == order_id))
    if existing:
        return existing

    order = db.scalar(select(Order).where(Order.id == order_id))
    if not order:
        raise AppError("NOT_FOUND", "Order not found", 404)

    delivery = Delivery(order_id=order.id, status="PENDING")
    db.add(delivery)
    db.flush()

    quote_lines = db.scalars(select(QuoteLine).where(QuoteLine.quote_id == order.quote_id)).all()
    for ql in quote_lines:
        product = db.scalar(select(Product).where(Product.id == ql.product_id))
        if not product or product.category == "SERVICE":
            continue
        db.add(
            DeliveryLine(
                delivery_id=delivery.id,
                product_id=product.id,
                qty_required=ql.qty,
                qty_packed=0,
            )
        )

    db.flush()
    return delivery


def list_deliveries(db: Session, status: str | None = None) -> list[dict]:
    stmt = select(Delivery).order_by(Delivery.created_at.desc())
    if status:
        stmt = stmt.where(Delivery.status == status)
    deliveries = db.scalars(stmt).all()

    out = []
    for d in deliveries:
        order = db.scalar(select(Order).where(Order.id == d.order_id))
        out.append({
            "id": d.id,
            "order_id": d.order_id,
            "order_number": order.number if order else None,
            "status": d.status,
            "vehicle": d.vehicle,
            "dispatched_at": d.dispatched_at,
            "delivered_at": d.delivered_at,
            "created_at": d.created_at,
        })
    return out


def get_delivery_detail(db: Session, delivery_id: int) -> dict:
    delivery = db.scalar(select(Delivery).where(Delivery.id == delivery_id))
    if not delivery:
        raise AppError("NOT_FOUND", "Delivery not found", 404)

    order = db.scalar(select(Order).where(Order.id == delivery.order_id))
    lines = db.scalars(select(DeliveryLine).where(DeliveryLine.delivery_id == delivery.id)).all()
    scans = db.scalars(select(DeliveryScan).where(DeliveryScan.delivery_id == delivery.id)).all()

    line_items = []
    for ln in lines:
        prod = db.scalar(select(Product).where(Product.id == ln.product_id))
        line_scans = []
        for sc in scans:
            su = db.scalar(select(SerialUnit).where(SerialUnit.id == sc.serial_unit_id))
            if su and su.product_id == ln.product_id:
                line_scans.append({
                    "scan_id": sc.id,
                    "serial_unit_id": su.id,
                    "serial_no": su.serial_no,
                    "scanned_at": sc.scanned_at,
                })
        line_items.append({
            "id": ln.id,
            "product_id": ln.product_id,
            "sku": prod.sku if prod else "",
            "product_name": prod.name if prod else "",
            "tracks_serial": prod.tracks_serial if prod else False,
            "qty_required": ln.qty_required,
            "qty_packed": ln.qty_packed,
            "scanned_serials": line_scans,
        })

    return {
        "id": delivery.id,
        "order_id": delivery.order_id,
        "order_number": order.number if order else None,
        "status": delivery.status,
        "vehicle": delivery.vehicle,
        "dispatched_at": delivery.dispatched_at,
        "delivered_at": delivery.delivered_at,
        "lines": line_items,
    }


def scan_serial(db: Session, delivery_id: int, serial_no: str, user_id: int) -> dict:
    """Enforces R7: IN_STOCK only, row lock + unique constraint."""
    delivery = db.scalar(select(Delivery).where(Delivery.id == delivery_id).with_for_update())
    if not delivery:
        raise AppError("NOT_FOUND", "Delivery not found", 404)
    if delivery.status != "PENDING":
        raise AppError("RULE_VIOLATION", "Can only scan items when delivery is PENDING", 409)

    clean_sn = serial_no.strip()
    serial_unit = db.scalar(select(SerialUnit).where(SerialUnit.serial_no == clean_sn).with_for_update())
    if not serial_unit:
        raise AppError("NOT_FOUND", f"Serial number '{clean_sn}' not found in inventory", 404)

    if serial_unit.status != "IN_STOCK" or serial_unit.delivery_id is not None:
        raise AppError(
            "RULE_VIOLATION",
            f"Serial '{clean_sn}' is not available (status: {serial_unit.status})",
            409,
        )

    line = db.scalar(
        select(DeliveryLine)
        .where(DeliveryLine.delivery_id == delivery.id, DeliveryLine.product_id == serial_unit.product_id)
        .with_for_update()
    )
    if not line:
        raise AppError("RULE_VIOLATION", f"Product for serial '{clean_sn}' is not on this pick list", 409)

    if line.qty_packed >= line.qty_required:
        raise AppError("RULE_VIOLATION", f"Required quantity ({line.qty_required}) already scanned for this item", 409)

    serial_unit.delivery_id = delivery.id
    line.qty_packed += 1

    scan = DeliveryScan(
        delivery_id=delivery.id,
        serial_unit_id=serial_unit.id,
        scanned_by_id=user_id,
        scanned_at=datetime.now(timezone.utc),
    )
    db.add(scan)
    db.flush()
    return get_delivery_detail(db, delivery.id)


def unscan_serial(db: Session, delivery_id: int, serial_unit_id: int) -> dict:
    delivery = db.scalar(select(Delivery).where(Delivery.id == delivery_id).with_for_update())
    if not delivery:
        raise AppError("NOT_FOUND", "Delivery not found", 404)
    if delivery.status != "PENDING":
        raise AppError("RULE_VIOLATION", "Cannot remove scans after dispatch", 409)

    scan = db.scalar(
        select(DeliveryScan).where(
            DeliveryScan.delivery_id == delivery.id,
            DeliveryScan.serial_unit_id == serial_unit_id,
        )
    )
    if not scan:
        raise AppError("NOT_FOUND", "Scan record not found on this delivery", 404)

    serial_unit = db.scalar(select(SerialUnit).where(SerialUnit.id == serial_unit_id).with_for_update())
    line = db.scalar(
        select(DeliveryLine)
        .where(DeliveryLine.delivery_id == delivery.id, DeliveryLine.product_id == serial_unit.product_id)
        .with_for_update()
    )

    if serial_unit:
        serial_unit.delivery_id = None
    if line and line.qty_packed > 0:
        line.qty_packed -= 1

    db.delete(scan)
    db.flush()
    return get_delivery_detail(db, delivery.id)


def _require_serial_scans(db: Session, delivery_id: int, lines: list[DeliveryLine]) -> None:
    scanned = dict(
        db.execute(
            select(SerialUnit.product_id, func.count(DeliveryScan.id))
            .select_from(DeliveryScan)
            .join(SerialUnit, SerialUnit.id == DeliveryScan.serial_unit_id)
            .where(DeliveryScan.delivery_id == delivery_id)
            .group_by(SerialUnit.product_id)
        ).all()
    )
    for line in lines:
        product = db.get(Product, line.product_id)
        count = scanned.get(line.product_id, 0)
        if product.tracks_serial and count != line.qty_required:
            raise AppError(
                "INCOMPLETE_SERIAL_SCANS",
                f"{product.name} requires {line.qty_required} serials, scanned {count}.",
                409,
            )


def dispatch(db: Session, delivery_id: int, vehicle: str | None = None) -> dict:
    """Enforces R6: all serialized lines must be fully scanned before dispatch."""
    delivery = db.scalar(select(Delivery).where(Delivery.id == delivery_id).with_for_update())
    if not delivery:
        raise AppError("NOT_FOUND", "Delivery not found", 404)
    if delivery.status != "PENDING":
        raise AppError("RULE_VIOLATION", f"Cannot dispatch from status {delivery.status}", 409)

    order = db.scalar(select(Order).where(Order.id == delivery.order_id).with_for_update())
    lines = list(db.scalars(
        select(DeliveryLine).where(DeliveryLine.delivery_id == delivery.id).order_by(DeliveryLine.product_id)
    ))
    _require_serial_scans(db, delivery.id, lines)
    for ln in lines:
        prod = adjust_stock(db, ln.product_id, -ln.qty_required)

        if not prod.tracks_serial:
            ln.qty_packed = ln.qty_required

        db.add(
            StockMovement(
                product_id=prod.id,
                qty=-ln.qty_required,
                reason="DISPATCH",
                ref_type="DELIVERY",
                ref_id=delivery.id,
                cost_paise=prod.cost_paise,
            )
        )

    scans = db.scalars(select(DeliveryScan).where(DeliveryScan.delivery_id == delivery.id)).all()
    for sc in scans:
        su = db.scalar(select(SerialUnit).where(SerialUnit.id == sc.serial_unit_id).with_for_update())
        if su:
            su.status = "DISPATCHED"
            su.customer_id = order.customer_id if order else None

    delivery.status = "DISPATCHED"
    delivery.vehicle = vehicle
    delivery.dispatched_at = datetime.now(timezone.utc)
    mark_dispatched(db, delivery.order_id)

    db.flush()
    return get_delivery_detail(db, delivery.id)


def complete(db: Session, delivery_id: int, delivered_by_id: int | None = None) -> dict:
    """Contract: marks delivery DELIVERED, sets serials INSTALLED, and calls warranty.service.start_for_delivery."""
    delivery = db.scalar(select(Delivery).where(Delivery.id == delivery_id).with_for_update())
    if not delivery:
        raise AppError("NOT_FOUND", "Delivery not found", 404)
    if delivery.status != "DISPATCHED":
        raise AppError("RULE_VIOLATION", "Delivery must be DISPATCHED before marking DELIVERED", 409)
    lines = list(db.scalars(select(DeliveryLine).where(DeliveryLine.delivery_id == delivery.id)))
    _require_serial_scans(db, delivery.id, lines)

    now = datetime.now(timezone.utc)
    delivery.status = "DELIVERED"
    delivery.delivered_at = now
    delivery.delivered_by_id = delivered_by_id

    order = db.scalar(select(Order).where(Order.id == delivery.order_id))
    scans = db.scalars(select(DeliveryScan).where(DeliveryScan.delivery_id == delivery.id)).all()
    for sc in scans:
        su = db.scalar(select(SerialUnit).where(SerialUnit.id == sc.serial_unit_id).with_for_update())
        if su:
            su.status = "INSTALLED"
            su.installed_at = now
            su.customer_id = order.customer_id if order else None

    db.flush()
    warranty_service.start_for_delivery(db, delivery.id)
    db.flush()
    return get_delivery_detail(db, delivery.id)
