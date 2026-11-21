from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.core.errors import AppError
from app.core.pagination import Pagination
from app.modules.catalog.models import Product
from app.modules.catalog.service import adjust_stock
from app.modules.inventory.models import SerialUnit, StockMovement
from app.modules.inventory.schemas import StockReceiveIn


def list_stock(db: Session, paging: Pagination, q: str | None = None, low_stock_only: bool = False) -> tuple[list[dict], int]:
    stmt = select(Product)
    if q:
        stmt = stmt.where(Product.name.ilike(f"%{q}%") | Product.sku.ilike(f"%{q}%"))
    if low_stock_only:
        stmt = stmt.where(Product.on_hand <= Product.reorder_level)
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    products = db.scalars(stmt.order_by(Product.name, Product.id).offset(paging.offset).limit(paging.page_size))

    result = []
    for p in products:
        is_low = p.on_hand <= p.reorder_level
        result.append({
            "id": p.id,
            "sku": p.sku,
            "name": p.name,
            "category": p.category,
            "unit": p.unit,
            "tracks_serial": p.tracks_serial,
            "on_hand": p.on_hand,
            "reorder_level": p.reorder_level,
            "low_stock": is_low,
            "cost_paise": p.cost_paise,
            "price_paise": p.price_paise,
        })
    return result, total


def receive_stock(db: Session, payload: StockReceiveIn) -> dict:
    product = db.scalar(select(Product).where(Product.id == payload.product_id).with_for_update())
    if not product:
        raise AppError("NOT_FOUND", "Product not found", 404)

    cleaned_serials = [s.strip() for s in payload.serial_numbers if s.strip()]

    if product.tracks_serial:
        if len(cleaned_serials) != payload.qty:
            raise AppError(
                "RULE_VIOLATION",
                f"Product tracks serials: expected {payload.qty} serial numbers, got {len(cleaned_serials)}",
                409,
            )
        if len(set(cleaned_serials)) != len(cleaned_serials):
            raise AppError("RULE_VIOLATION", "Duplicate serial numbers in batch", 409)

        existing = db.scalars(select(SerialUnit.serial_no).where(SerialUnit.serial_no.in_(cleaned_serials))).all()
        if existing:
            raise AppError("RULE_VIOLATION", f"Serial numbers already exist: {', '.join(existing)}", 409)

        for sn in cleaned_serials:
            db.add(
                SerialUnit(
                    product_id=product.id,
                    serial_no=sn,
                    status="IN_STOCK",
                    purchase_cost_paise=payload.purchase_cost_paise,
                )
            )
    else:
        if cleaned_serials:
            raise AppError("RULE_VIOLATION", "This product does not track serial numbers", 409)

    movement = StockMovement(
        product_id=product.id,
        qty=payload.qty,
        reason="PURCHASE",
        ref_type="RECEIVE",
        cost_paise=payload.purchase_cost_paise,
    )
    db.add(movement)

    try:
        product = adjust_stock(db, product.id, payload.qty, payload.purchase_cost_paise)
    except IntegrityError as exc:
        constraint = getattr(getattr(exc.orig, "diag", None), "constraint_name", None)
        if constraint == "ix_serial_units_serial_no" or "UNIQUE constraint failed: serial_units.serial_no" in str(exc.orig):
            raise AppError("DUPLICATE_SERIAL", "A received serial number is already in use.", 409) from exc
        raise
    return {"product_id": product.id, "added_qty": payload.qty, "new_on_hand": product.on_hand}
