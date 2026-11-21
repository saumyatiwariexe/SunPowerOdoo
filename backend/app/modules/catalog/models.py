from enum import StrEnum

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Enum,
    ForeignKey,
    String,
    UniqueConstraint,
    false,
    true,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base, TimestampMixin

INSTALLATION_SKU = "INSTALLATION"


class ProductCategory(StrEnum):
    PANEL = "PANEL"
    INVERTER = "INVERTER"
    BATTERY = "BATTERY"
    CHARGE_CONTROLLER = "CHARGE_CONTROLLER"
    STAND = "STAND"
    WIRING = "WIRING"
    SAFETY = "SAFETY"
    SERVICE = "SERVICE"


class Product(TimestampMixin, Base):
    __tablename__ = "products"
    __table_args__ = (
        CheckConstraint("cost_paise >= 0", name="ck_products_cost_paise"),
        CheckConstraint("price_paise >= 0", name="ck_products_price_paise"),
        CheckConstraint("reorder_level >= 0", name="ck_products_reorder_level"),
        CheckConstraint("warranty_months > 0", name="ck_products_warranty_months"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    sku: Mapped[str] = mapped_column(String(64), unique=True)
    name: Mapped[str] = mapped_column(String(120))
    category: Mapped[ProductCategory] = mapped_column(
        Enum(
            ProductCategory,
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
            name="product_category",
        )
    )
    unit: Mapped[str] = mapped_column(String(24))
    tracks_serial: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())
    warranty_months: Mapped[int | None]
    cost_paise: Mapped[int] = mapped_column(BigInteger)
    price_paise: Mapped[int] = mapped_column(BigInteger)
    reorder_level: Mapped[int] = mapped_column(default=0, server_default="0")
    on_hand: Mapped[int] = mapped_column(default=0, server_default="0")


class SystemType(StrEnum):
    ON_GRID = "ON_GRID"
    OFF_GRID = "OFF_GRID"


class Package(TimestampMixin, Base):
    __tablename__ = "packages"
    __table_args__ = (
        CheckConstraint("price_paise >= 0", name="ck_packages_price_paise"),
        CheckConstraint(
            "(system_type IS NULL AND capacity_kw IS NULL) OR "
            "(system_type IS NOT NULL AND capacity_kw IS NOT NULL AND capacity_kw BETWEEN 1 AND 5)",
            name="ck_packages_system_capacity",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    system_type: Mapped[SystemType | None] = mapped_column(
        Enum(
            SystemType,
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
            name="package_system_type",
        )
    )
    capacity_kw: Mapped[int | None]
    price_paise: Mapped[int] = mapped_column(BigInteger)
    active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true())
    items: Mapped[list["PackageItem"]] = relationship(
        cascade="all, delete-orphan", order_by="PackageItem.product_id"
    )


class PackageItem(TimestampMixin, Base):
    __tablename__ = "package_items"
    __table_args__ = (
        CheckConstraint("qty > 0", name="ck_package_items_qty"),
        UniqueConstraint("package_id", "product_id", name="uq_package_items_package_product"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    package_id: Mapped[int] = mapped_column(ForeignKey("packages.id", ondelete="CASCADE"))
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), index=True)
    qty: Mapped[int]
    product: Mapped[Product] = relationship()
