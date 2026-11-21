from enum import StrEnum

from sqlalchemy import BigInteger, Boolean, CheckConstraint, Enum, String, false
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, TimestampMixin


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
