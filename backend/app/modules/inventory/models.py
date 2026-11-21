from datetime import datetime
from sqlalchemy import BigInteger, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from app.core.db import Base, TimestampMixin, UTCDateTime


class StockMovement(TimestampMixin, Base):
    __tablename__ = "stock_movements"

    id: Mapped[int] = mapped_column(primary_key=True)

    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False, index=True)
    qty: Mapped[int] = mapped_column(Integer, nullable=False)  # + for in, - for out
    reason: Mapped[str] = mapped_column(String(32), nullable=False)  # PURCHASE, DISPATCH, ADJUSTMENT, RETURN
    ref_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    ref_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cost_paise: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)


class SerialUnit(TimestampMixin, Base):
    __tablename__ = "serial_units"

    id: Mapped[int] = mapped_column(primary_key=True)

    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False, index=True)
    serial_no: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="IN_STOCK", index=True
    )  # IN_STOCK, DISPATCHED, INSTALLED
    purchase_cost_paise: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    delivery_id: Mapped[int | None] = mapped_column(ForeignKey("deliveries.id"), nullable=True)
    customer_id: Mapped[int | None] = mapped_column(ForeignKey("customers.id"), nullable=True)
    installed_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
