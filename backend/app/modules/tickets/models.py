from datetime import datetime
from enum import StrEnum

from sqlalchemy import BigInteger, Boolean, CheckConstraint, Enum, ForeignKey, String, Text, false
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base, TimestampMixin, UTCDateTime


class TicketStatus(StrEnum):
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"


class TicketPriority(StrEnum):
    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"
    URGENT = "URGENT"


class TicketLineType(StrEnum):
    PART = "PART"
    LABOUR = "LABOUR"


class Ticket(TimestampMixin, Base):
    __tablename__ = "tickets"

    id: Mapped[int] = mapped_column(primary_key=True)
    number: Mapped[str] = mapped_column(String(24), unique=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), index=True)
    serial_unit_id: Mapped[int] = mapped_column(ForeignKey("serial_units.id"), index=True)
    warranty_id: Mapped[int | None] = mapped_column(ForeignKey("warranties.id"))
    fault_code: Mapped[str] = mapped_column(String(64))
    description: Mapped[str] = mapped_column(Text)
    priority: Mapped[TicketPriority] = mapped_column(
        Enum(TicketPriority, native_enum=False, create_constraint=True, name="ticket_priority"),
        default=TicketPriority.NORMAL, server_default="NORMAL",
    )
    status: Mapped[TicketStatus] = mapped_column(
        Enum(TicketStatus, native_enum=False, create_constraint=True, name="ticket_status"),
        default=TicketStatus.OPEN, server_default="OPEN", index=True,
    )
    assigned_to_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True)
    resolution: Mapped[str | None] = mapped_column(Text)
    customer_confirmed_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    billable: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())
    lines: Mapped[list["TicketLine"]] = relationship(
        cascade="all, delete-orphan", order_by="TicketLine.id"
    )


class TicketLine(TimestampMixin, Base):
    __tablename__ = "ticket_lines"
    __table_args__ = (
        CheckConstraint("qty > 0", name="ck_ticket_lines_qty"),
        CheckConstraint("unit_price_paise >= 0", name="ck_ticket_lines_unit_price"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    ticket_id: Mapped[int] = mapped_column(ForeignKey("tickets.id", ondelete="CASCADE"), index=True)
    type: Mapped[TicketLineType] = mapped_column(
        Enum(TicketLineType, native_enum=False, create_constraint=True, name="ticket_line_type")
    )
    product_id: Mapped[int | None] = mapped_column(ForeignKey("products.id"))
    description: Mapped[str] = mapped_column(String(255))
    qty: Mapped[int]
    unit_price_paise: Mapped[int] = mapped_column(BigInteger)
