from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.catalog.models import Product
from app.modules.inventory.models import SerialUnit, StockMovement
from .seed_b import seed_person_b


def seed_inventory(db: Session) -> None:
    seed_person_b(db)
    # Earlier demos seeded bulk controllers. Label only untouched demo opening
    # stock. Physical stock must retain the manufacturer's actual serial numbers.
    controller = db.scalar(select(Product).where(Product.sku == "CONTROLLER").with_for_update())
    if controller is None or not controller.tracks_serial or not controller.on_hand:
        return
    units = select(SerialUnit.id).where(SerialUnit.product_id == controller.id)
    if db.scalar(units.limit(1)) is not None:
        return
    moves = db.scalars(select(StockMovement).where(StockMovement.product_id == controller.id)).all()
    if len(moves) != 1:
        return
    opening = moves[0]
    if (opening.reason, opening.ref_type, opening.qty) != ("PURCHASE", "SEED", controller.on_hand):
        return
    for i in range(1, opening.qty + 1):
        db.add(SerialUnit(product_id=controller.id, serial_no=f"CONTROLLER-SN-{i:04d}",
                          purchase_cost_paise=opening.cost_paise))
    db.flush()
