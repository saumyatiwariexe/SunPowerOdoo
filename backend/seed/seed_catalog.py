from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.catalog.models import INSTALLATION_SKU, Package, Product, ProductCategory, SystemType
from app.modules.catalog.schemas import PackageCreate, PackageItemInput
from app.modules.catalog.service import create_package

PRODUCTS = (
    ("PANEL-500", "Solar panel 500 W", ProductCategory.PANEL, 750_000, 950_000, 240),
    ("STAND", "Panel mounting stand", ProductCategory.STAND, 70_000, 100_000, None),
    ("WIRING", "Wiring kit", ProductCategory.WIRING, 110_000, 150_000, None),
    ("SAFETY", "DC protection kit", ProductCategory.SAFETY, 90_000, 130_000, None),
    ("BATTERY", "Battery module", ProductCategory.BATTERY, 850_000, 1_100_000, 24),
    ("CONTROLLER", "Charge controller", ProductCategory.CHARGE_CONTROLLER, 200_000, 290_000, None),
    (INSTALLATION_SKU, "Installation service", ProductCategory.SERVICE, 380_000, 600_000, None),
)


def seed_catalog(db: Session) -> None:
    """Seed demo catalog records while preserving existing products and packages."""
    products = {product.sku: product for product in db.scalars(select(Product))}
    inverters = (
        (f"INV-{kw}", f"Hybrid inverter {kw} kW", ProductCategory.INVERTER, kw * 580_000, kw * 750_000, 24)
        for kw in range(1, 6)
    )
    for sku, name, category, cost, price, months in (*PRODUCTS, *inverters):
        if sku not in products:
            product = Product(
                sku=sku,
                name=name,
                category=category,
                cost_paise=cost,
                price_paise=price,
                warranty_months=months,
                tracks_serial=months is not None,
                unit="job" if category == ProductCategory.SERVICE else "unit",
            )
            products[sku] = product
            db.add(product)
    db.flush()

    existing = set(db.scalars(select(Package.name)))
    specs = [("Solar Panel Set", None, None, {"PANEL-500": 2, "STAND": 1, "WIRING": 1})]
    for kw in range(1, 6):
        for label, system_type in (("On-Grid", SystemType.ON_GRID), ("Off-Grid", SystemType.OFF_GRID)):
            parts = {
                "PANEL-500": kw * 2,
                "STAND": kw,
                "WIRING": 1,
                "SAFETY": 1,
                f"INV-{kw}": 1,
                INSTALLATION_SKU: 1,
            }
            if system_type == SystemType.OFF_GRID:
                parts.update(BATTERY=kw, CONTROLLER=1)
            specs.append((f"{label} {kw} kW", system_type, kw, parts))

    for name, system_type, capacity_kw, parts in specs:
        if name in existing:
            continue
        create_package(
            db,
            PackageCreate(
                name=name,
                system_type=system_type,
                capacity_kw=capacity_kw,
                price_paise=sum(products[sku].price_paise * qty for sku, qty in parts.items()),
                items=[PackageItemInput(product_id=products[sku].id, qty=qty) for sku, qty in parts.items()],
            ),
        )
