from datetime import datetime
from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.core.db import Base, TimestampMixin, UTCDateTime


class Delivery(TimestampMixin, Base):
    __tablename__ = "deliveries"

    id: Mapped[int] = mapped_column(primary_key=True)

    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), unique=True, nullable=False)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="PENDING", index=True
    )  # PENDING, DISPATCHED, DELIVERED
    vehicle: Mapped[str | None] = mapped_column(String(100), nullable=True)
    dispatched_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    delivered_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)


class DeliveryLine(TimestampMixin, Base):
    __tablename__ = "delivery_lines"

    id: Mapped[int] = mapped_column(primary_key=True)

    delivery_id: Mapped[int] = mapped_column(ForeignKey("deliveries.id"), nullable=False, index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)
    qty_required: Mapped[int] = mapped_column(Integer, nullable=False)
    qty_packed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class DeliveryScan(TimestampMixin, Base):
    __tablename__ = "delivery_scans"
    __table_args__ = (UniqueConstraint("serial_unit_id", name="uq_delivery_scans_serial_unit_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)

    delivery_id: Mapped[int] = mapped_column(ForeignKey("deliveries.id"), nullable=False, index=True)
    serial_unit_id: Mapped[int] = mapped_column(ForeignKey("serial_units.id"), nullable=False)
    scanned_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    scanned_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
