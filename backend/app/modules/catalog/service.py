from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.core.errors import AppError
from app.core.pagination import Pagination

from .models import INSTALLATION_SKU, Package, PackageItem, Product, ProductCategory, SystemType
from .schemas import PackageCreate, PackageItemInput, PackagePatch, ProductCreate, ProductPatch


def _flush_catalog(db: Session) -> None:
    try:
        db.flush()
    except IntegrityError as exc:
        constraint = getattr(getattr(exc.orig, "diag", None), "constraint_name", None)
        if constraint == "products_sku_key" or "UNIQUE constraint failed: products.sku" in str(exc.orig):
            raise AppError("DUPLICATE_SKU", "A product already uses that SKU.", 409) from exc
        if constraint == "packages_name_key" or "UNIQUE constraint failed: packages.name" in str(exc.orig):
            raise AppError("DUPLICATE_PACKAGE", "A package already uses that name.", 409) from exc
        raise


def list_products(db: Session, pagination: Pagination, q: str = "") -> tuple[list[Product], int]:
    filters = []
    if q:
        filters.append(or_(Product.name.icontains(q, autoescape=True), Product.sku.icontains(q, autoescape=True)))
    total = db.scalar(select(func.count()).select_from(Product).where(*filters))
    query = select(Product).where(*filters).order_by(Product.id)
    rows = db.scalars(query.offset(pagination.offset).limit(pagination.page_size)).all()
    return list(rows), total or 0


def get_product(db: Session, product_id: int, *, for_update: bool = False) -> Product:
    product = db.get(Product, product_id, with_for_update=for_update, populate_existing=for_update)
    if product is None:
        raise AppError("PRODUCT_NOT_FOUND", "Product not found.", 404)
    return product


def create_product(db: Session, payload: ProductCreate) -> Product:
    _validate_installation_product(payload.sku, payload.category)
    product = Product(**payload.model_dump())
    db.add(product)
    _flush_catalog(db)
    return product


def adjust_stock(db: Session, product_id: int, change: int, cost_paise: int | None = None) -> Product:
    product = get_product(db, product_id, for_update=True)
    quantity = product.on_hand + change
    if quantity < 0:
        raise AppError("INSUFFICIENT_STOCK", f"Insufficient stock on hand for {product.name}.", 409)
    if quantity > 2_147_483_647:
        raise AppError("STOCK_QUANTITY_TOO_LARGE", "The new stock count exceeds the supported range.", 409)
    product.on_hand = quantity
    if cost_paise is not None:
        product.cost_paise = cost_paise
    db.flush()
    return product


def update_product(db: Session, product_id: int, payload: ProductPatch) -> Product:
    product = get_product(db, product_id, for_update=True)
    changes = payload.model_dump(exclude_unset=True)
    sku = changes.get("sku", product.sku)
    if product.sku == INSTALLATION_SKU and sku != INSTALLATION_SKU:
        raise AppError("INSTALLATION_SKU_REQUIRED", "The installation product SKU is fixed.", 409)
    _validate_installation_product(sku, changes.get("category", product.category))
    for field, value in changes.items():
        setattr(product, field, value)
    _flush_catalog(db)
    return product


def _validate_installation_product(sku: str, category: ProductCategory) -> None:
    if sku == INSTALLATION_SKU and category != ProductCategory.SERVICE:
        raise AppError("INVALID_INSTALLATION_PRODUCT", "Installation must be a service product.", 409)


def list_packages(
    db: Session, pagination: Pagination, q: str = "", active: bool | None = None
) -> tuple[list[Package], int]:
    filters = []
    if q:
        filters.append(Package.name.icontains(q, autoescape=True))
    if active is not None:
        filters.append(Package.active.is_(active))
    total = db.scalar(select(func.count()).select_from(Package).where(*filters))
    query = select(Package).where(*filters).order_by(Package.id)
    rows = db.scalars(query.offset(pagination.offset).limit(pagination.page_size)).all()
    return list(rows), total or 0


def get_package(db: Session, package_id: int, *, for_update: bool = False) -> Package:
    package = db.get(Package, package_id, with_for_update=for_update, populate_existing=for_update)
    if package is None:
        raise AppError("PACKAGE_NOT_FOUND", "Package not found.", 404)
    return package


def get_package_bom(db: Session, package_id: int) -> list[PackageItem]:
    """Return the package's quantities and products for quote creation."""
    get_package(db, package_id)
    query = (
        select(PackageItem)
        .where(PackageItem.package_id == package_id)
        .options(joinedload(PackageItem.product))
        .order_by(PackageItem.product_id)
    )
    return list(db.scalars(query))


def _check_installation(system_type: SystemType | None, has_installation: bool) -> None:
    if system_type is not None and not has_installation:
        raise AppError("INSTALLATION_REQUIRED", "Solar system packages require an installation line.", 409)


def _replace_items(
    db: Session, package: Package, items: list[PackageItemInput], system_type: SystemType | None
) -> None:
    product_ids = {item.product_id for item in items}
    product_rows = db.execute(select(Product.id, Product.sku).where(Product.id.in_(product_ids)))
    products = {row.id: row.sku for row in product_rows}
    if missing := sorted(product_ids - products.keys()):
        missing_text = ", ".join(map(str, missing))
        raise AppError("INVALID_BOM_PRODUCT", f"Unknown product IDs: {missing_text}.", 409)
    _check_installation(system_type, INSTALLATION_SKU in products.values())

    current = {item.product_id: item for item in package.items}
    updated = []
    for item in sorted(items, key=lambda item: item.product_id):
        row = current.get(item.product_id)
        if row is None:
            row = PackageItem(product_id=item.product_id)
        row.qty = item.qty
        updated.append(row)
    package.items = updated


def create_package(db: Session, payload: PackageCreate) -> Package:
    package = Package(**payload.model_dump(exclude={"items"}))
    _replace_items(db, package, payload.items, payload.system_type)
    db.add(package)
    _flush_catalog(db)
    return package


def update_package(db: Session, package_id: int, payload: PackagePatch) -> Package:
    package = get_package(db, package_id, for_update=True)
    fields = payload.model_dump(exclude_unset=True, exclude={"items"})
    system_type = fields.get("system_type", package.system_type)
    capacity_kw = fields.get("capacity_kw", package.capacity_kw)
    if (system_type is None) != (capacity_kw is None):
        raise AppError("INVALID_PACKAGE_CAPACITY", "Set both system type and capacity, or clear both.", 409)

    if payload.items is not None:
        _replace_items(db, package, payload.items, system_type)
    elif system_type is not None:
        _check_installation(
            system_type, any(item.product.sku == INSTALLATION_SKU for item in package.items)
        )
    for field, value in fields.items():
        setattr(package, field, value)
    _flush_catalog(db)
    return package
