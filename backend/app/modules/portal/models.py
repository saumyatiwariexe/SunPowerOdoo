from datetime import datetime
from sqlalchemy import BigInteger, CheckConstraint, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.core.db import Base, TimestampMixin, UTCDateTime


class CustomerAccount(TimestampMixin, Base):
    __tablename__ = "customer_accounts"

    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), unique=True)
    email: Mapped[str] = mapped_column(String(254), unique=True)
    password_hash: Mapped[str | None] = mapped_column(String(60))
    invite_hash: Mapped[str | None] = mapped_column(String(64), unique=True)
    invite_expires_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    invited_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    activated_at: Mapped[datetime | None] = mapped_column(UTCDateTime())


class CustomerPaymentReport(TimestampMixin, Base):
    __tablename__ = "customer_payment_reports"
    __table_args__ = (
        CheckConstraint("amount_paise > 0"),
        CheckConstraint("(order_id IS NOT NULL AND invoice_id IS NULL) OR (order_id IS NULL AND invoice_id IS NOT NULL)"),
        CheckConstraint("status IN ('PENDING', 'VERIFIED', 'REJECTED')"),
        UniqueConstraint("method", "reference", name="uq_customer_payment_reference"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), index=True)
    order_id: Mapped[int | None] = mapped_column(ForeignKey("orders.id"), index=True)
    invoice_id: Mapped[int | None] = mapped_column(ForeignKey("invoices.id"), index=True)
    amount_paise: Mapped[int] = mapped_column(BigInteger)
    method: Mapped[str] = mapped_column(String(10))
    reference: Mapped[str] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(10), default="PENDING", index=True)
    payment_id: Mapped[int | None] = mapped_column(ForeignKey("payments.id"), unique=True)
    reviewed_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True)
    review_note: Mapped[str | None] = mapped_column(String(500))
