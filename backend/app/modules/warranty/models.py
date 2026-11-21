from datetime import date
from sqlalchemy import Date, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column
from app.core.db import Base


class Warranty(Base):
    __tablename__ = "warranties"

    serial_unit_id: Mapped[int] = mapped_column(ForeignKey("serial_units.id"), unique=True, nullable=False)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), nullable=False, index=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), nullable=False, index=True)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="ACTIVE", index=True
    )  # ACTIVE, EXPIRED, VOID