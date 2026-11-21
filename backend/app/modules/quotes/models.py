from datetime import date
from enum import StrEnum

from sqlalchemy import BigInteger, CheckConstraint, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base, TimestampMixin


class QuoteStatus(StrEnum):
    DRAFT = "DRAFT"
    SENT = "SENT"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


class Quote(TimestampMixin, Base):
    __tablename__ = "quotes"
    __table_args__ = (
        CheckConstraint("subtotal_paise >= 0", name="ck_quotes_subtotal_paise"),
        CheckConstraint(
            "subsidy_paise >= 0 AND subsidy_paise <= subtotal_paise",
            name="ck_quotes_subsidy_paise",
        ),
        CheckConstraint("total_paise = subtotal_paise - subsidy_paise", name="ck_quotes_total_paise"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    number: Mapped[str] = mapped_column(String(24), unique=True)
    lead_id: Mapped[int] = mapped_column(ForeignKey("leads.id"), index=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), index=True)
    package_id: Mapped[int] = mapped_column(ForeignKey("packages.id"))
    status: Mapped[QuoteStatus] = mapped_column(
        Enum(QuoteStatus, native_enum=False, create_constraint=True, name="quote_status"),
        default=QuoteStatus.DRAFT,
        server_default="DRAFT",
        index=True,
    )
    subtotal_paise: Mapped[int] = mapped_column(BigInteger)
    subsidy_paise: Mapped[int] = mapped_column(BigInteger, default=0, server_default="0")
    total_paise: Mapped[int] = mapped_column(BigInteger)
    valid_until: Mapped[date]
    lines: Mapped[list["QuoteLine"]] = relationship(
        cascade="all, delete-orphan", order_by="QuoteLine.id"
    )


class QuoteLine(TimestampMixin, Base):
    __tablename__ = "quote_lines"
    __table_args__ = (
        CheckConstraint("qty > 0", name="ck_quote_lines_qty"),
        CheckConstraint("unit_price_paise >= 0", name="ck_quote_lines_price_paise"),
        CheckConstraint("line_paise = qty * unit_price_paise", name="ck_quote_lines_total_paise"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    quote_id: Mapped[int] = mapped_column(ForeignKey("quotes.id", ondelete="CASCADE"), index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    description: Mapped[str] = mapped_column(String(255))
    qty: Mapped[int]
    unit_price_paise: Mapped[int] = mapped_column(BigInteger)
    line_paise: Mapped[int] = mapped_column(BigInteger)
