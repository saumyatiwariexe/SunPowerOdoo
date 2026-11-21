from datetime import datetime
from sqlalchemy import BigInteger, CheckConstraint, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from app.core.db import Base, TimestampMixin, UTCDateTime


class Payment(TimestampMixin, Base):
    __tablename__ = "payments"
    __table_args__ = (
        CheckConstraint("order_id IS NOT NULL OR invoice_id IS NOT NULL", name="ck_payment_target"),
        CheckConstraint("amount_paise > 0", name="ck_payment_positive"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    order_id: Mapped[int | None] = mapped_column(ForeignKey("orders.id"), nullable=True, index=True)
    invoice_id: Mapped[int | None] = mapped_column(ForeignKey("invoices.id"), nullable=True, index=True)
    amount_paise: Mapped[int] = mapped_column(BigInteger, nullable=False)
    method: Mapped[str] = mapped_column(String(32), nullable=False)  # CASH, CARD, UPI, BANK
    reference: Mapped[str | None] = mapped_column(String(100), nullable=True)
    paid_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    received_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)


class Invoice(TimestampMixin, Base):
    __tablename__ = "invoices"
    __table_args__ = (
        CheckConstraint("order_id IS NOT NULL OR ticket_id IS NOT NULL", name="ck_invoice_target"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    number: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    order_id: Mapped[int | None] = mapped_column(ForeignKey("orders.id"), nullable=True, unique=True)
    ticket_id: Mapped[int | None] = mapped_column(ForeignKey("tickets.id"), nullable=True, unique=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="SENT", index=True
    )  # DRAFT, SENT, PAID, PARTIAL
    total_paise: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    paid_paise: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    issued_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)


class InvoiceLine(TimestampMixin, Base):
    __tablename__ = "invoice_lines"

    id: Mapped[int] = mapped_column(primary_key=True)

    invoice_id: Mapped[int] = mapped_column(ForeignKey("invoices.id"), nullable=False, index=True)
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    qty: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price_paise: Mapped[int] = mapped_column(BigInteger, nullable=False)
