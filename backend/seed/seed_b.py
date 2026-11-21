from datetime import date, datetime, timedelta, timezone
from dateutil.relativedelta import relativedelta
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.billing.models import Invoice, InvoiceLine, Payment
from app.modules.catalog.models import Product
from app.modules.deliveries.models import Delivery, DeliveryLine, DeliveryScan
from app.modules.inventory.models import SerialUnit, StockMovement
from app.modules.orders.models import Order
from app.modules.users.models import Customer, User
from app.modules.warranty.models import Warranty


def seed_person_b(db: Session) -> None:
    # Idempotency check
    if db.scalar(select(SerialUnit).limit(1)):
        return

    products = db.scalars(select(Product)).all()
    warehouse_user = db.scalar(select(User).where(User.role == "WAREHOUSE"))
    director_user = db.scalar(select(User).where(User.role == "DIRECTOR"))
    actor_id = warehouse_user.id if warehouse_user else (director_user.id if director_user else 1)

    panel_prod = None
    inverter_prod = None

    # 1. Seed opening stock & serial units for all catalog products
    for prod in products:
        if prod.category == "SERVICE":
            continue
        if prod.category == "PANEL" and not panel_prod:
            panel_prod = prod
        if prod.category == "INVERTER" and not inverter_prod:
            inverter_prod = prod

        qty = 25 if prod.tracks_serial else 100
        prod.on_hand = qty
        db.add(
            StockMovement(
                product_id=prod.id,
                qty=qty,
                reason="PURCHASE",
                ref_type="SEED",
                cost_paise=prod.cost_paise,
            )
        )
        if prod.tracks_serial:
            for idx in range(1, qty + 1):
                db.add(
                    SerialUnit(
                        product_id=prod.id,
                        serial_no=f"{prod.sku}-SN-{idx:04d}",
                        status="IN_STOCK",
                        purchase_cost_paise=prod.cost_paise,
                    )
                )

    db.flush()

    # 2. Seed an old delivered order (26 months ago) so inverter warranty is EXPIRED (24m)
    #    while panel warranty is still ACTIVE (240m) for Demo Scene 7 & 8.
    old_order = db.scalar(select(Order).where(Order.status == "CLOSED").limit(1))
    if not old_order:
        old_order = db.scalar(select(Order).order_by(Order.id.asc()).limit(1))

    if old_order and inverter_prod and panel_prod:
        delivered_dt = datetime.now(timezone.utc) - relativedelta(months=26)
        delivered_date = delivered_dt.date()

        old_delivery = Delivery(
            order_id=old_order.id,
            status="DELIVERED",
            vehicle="PB-08-SOLAR-01",
            dispatched_at=delivered_dt - timedelta(hours=3),
            delivered_at=delivered_dt,
            delivered_by_id=actor_id,
        )
        db.add(old_delivery)
        db.flush()

        # Assign 1 old inverter serial (EXPIRED warranty: 24 months)
        old_inv_sn = SerialUnit(
            product_id=inverter_prod.id,
            serial_no="INV-OLD-2024-001",
            status="INSTALLED",
            purchase_cost_paise=inverter_prod.cost_paise,
            delivery_id=old_delivery.id,
            customer_id=old_order.customer_id,
            installed_at=delivered_dt,
        )
        db.add(old_inv_sn)
        db.flush()

        db.add(DeliveryLine(delivery_id=old_delivery.id, product_id=inverter_prod.id, qty_required=1, qty_packed=1))
        db.add(
            DeliveryScan(
                delivery_id=old_delivery.id,
                serial_unit_id=old_inv_sn.id,
                scanned_by_id=actor_id,
                scanned_at=delivered_dt - timedelta(hours=4),
            )
        )

        inv_end_date = delivered_date + relativedelta(months=inverter_prod.warranty_months or 24)
        db.add(
            Warranty(
                serial_unit_id=old_inv_sn.id,
                customer_id=old_order.customer_id,
                order_id=old_order.id,
                start_date=delivered_date,
                end_date=inv_end_date,
                status="EXPIRED" if date.today() > inv_end_date else "ACTIVE",
            )
        )

        # Assign 1 old panel serial (ACTIVE warranty: 240 months)
        old_pnl_sn = SerialUnit(
            product_id=panel_prod.id,
            serial_no="PNL-OLD-2024-001",
            status="INSTALLED",
            purchase_cost_paise=panel_prod.cost_paise,
            delivery_id=old_delivery.id,
            customer_id=old_order.customer_id,
            installed_at=delivered_dt,
        )
        db.add(old_pnl_sn)
        db.flush()

        db.add(DeliveryLine(delivery_id=old_delivery.id, product_id=panel_prod.id, qty_required=1, qty_packed=1))
        db.add(
            DeliveryScan(
                delivery_id=old_delivery.id,
                serial_unit_id=old_pnl_sn.id,
                scanned_by_id=actor_id,
                scanned_at=delivered_dt - timedelta(hours=4),
            )
        )

        pnl_end_date = delivered_date + relativedelta(months=panel_prod.warranty_months or 240)
        db.add(
            Warranty(
                serial_unit_id=old_pnl_sn.id,
                customer_id=old_order.customer_id,
                order_id=old_order.id,
                start_date=delivered_date,
                end_date=pnl_end_date,
                status="ACTIVE" if date.today() <= pnl_end_date else "EXPIRED",
            )
        )

        # Paid invoice for the old order
        old_inv = Invoice(
            number="INV-0000",
            order_id=old_order.id,
            customer_id=old_order.customer_id,
            status="PAID",
            total_paise=old_order.total_paise,
            paid_paise=old_order.total_paise,
            issued_at=delivered_dt,
        )
        db.add(old_inv)
        db.flush()

        db.add(
            InvoiceLine(
                invoice_id=old_inv.id,
                description=f"Rooftop Solar Installation ({old_order.number})",
                qty=1,
                unit_price_paise=old_order.total_paise,
            )
        )
        db.add(
            Payment(
                order_id=old_order.id,
                invoice_id=old_inv.id,
                amount_paise=old_order.total_paise,
                method="BANK",
                reference="NEFT-SEED-2024",
                paid_at=delivered_dt,
                received_by_id=actor_id,
            )
        )

    db.flush()