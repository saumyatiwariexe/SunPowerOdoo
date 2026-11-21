from datetime import datetime
from enum import StrEnum

from sqlalchemy import BigInteger, CheckConstraint, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, TimestampMixin, UTCDateTime


class OrderStatus(StrEnum):
    DRAFT = "DRAFT"
    CONFIRMED = "CONFIRMED"
    DISPATCHED = "DISPATCHED"
    INSTALLED = "INSTALLED"
    CLOSED = "CLOSED"
    CANCELLED = "CANCELLED"


class Order(TimestampMixin, Base):
    __tablename__ = "orders"
    __table_args__ = (
        CheckConstraint("total_paise >= 0", name="ck_orders_total_paise"),
        CheckConstraint(
            "advance_min_paise >= 0 AND advance_min_paise <= total_paise",
            name="ck_orders_advance_min_paise",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    number: Mapped[str] = mapped_column(String(24), unique=True)
    quote_id: Mapped[int] = mapped_column(ForeignKey("quotes.id"), unique=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), index=True)
    status: Mapped[OrderStatus] = mapped_column(
        Enum(OrderStatus, native_enum=False, create_constraint=True, name="order_status"),
        default=OrderStatus.DRAFT,
        server_default="DRAFT",
        index=True,
    )
    total_paise: Mapped[int] = mapped_column(BigInteger)
    advance_min_paise: Mapped[int] = mapped_column(BigInteger)
    confirmed_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
