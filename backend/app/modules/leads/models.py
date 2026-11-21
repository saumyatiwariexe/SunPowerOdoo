from datetime import datetime
from enum import StrEnum

from sqlalchemy import BigInteger, Boolean, Enum, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base, TimestampMixin, UTCDateTime


class LeadSource(StrEnum):
    WEB = "WEB"
    WHATSAPP = "WHATSAPP"
    CALL = "CALL"


class SystemType(StrEnum):
    ON_GRID = "ON_GRID"
    OFF_GRID = "OFF_GRID"


class LeadStatus(StrEnum):
    NEW = "NEW"
    CONTACTED = "CONTACTED"
    SURVEY_PENDING = "SURVEY_PENDING"
    SURVEY_DONE = "SURVEY_DONE"
    QUOTED = "QUOTED"
    WON = "WON"
    LOST = "LOST"


# Valid forward transitions for the Lead state machine
LEAD_TRANSITIONS: dict[LeadStatus, set[LeadStatus]] = {
    LeadStatus.NEW: {LeadStatus.CONTACTED, LeadStatus.LOST},
    LeadStatus.CONTACTED: {LeadStatus.SURVEY_PENDING, LeadStatus.LOST},
    LeadStatus.SURVEY_PENDING: {LeadStatus.SURVEY_DONE, LeadStatus.LOST},
    LeadStatus.SURVEY_DONE: {LeadStatus.QUOTED, LeadStatus.LOST},
    LeadStatus.QUOTED: {LeadStatus.WON, LeadStatus.LOST},
    LeadStatus.WON: set(),
    LeadStatus.LOST: set(),
}


class Lead(TimestampMixin, Base):
    __tablename__ = "leads"
    __table_args__ = (Index("ix_leads_status", "status"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"))
    source: Mapped[LeadSource] = mapped_column(
        Enum(LeadSource, native_enum=False, create_constraint=True, validate_strings=True, name="lead_source")
    )
    requested_kw: Mapped[float]
    system_type: Mapped[SystemType] = mapped_column(
        Enum(SystemType, native_enum=False, create_constraint=True, validate_strings=True, name="system_type")
    )
    subsidy_interest: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[LeadStatus] = mapped_column(
        Enum(LeadStatus, native_enum=False, create_constraint=True, validate_strings=True, name="lead_status"),
        default=LeadStatus.NEW,
        server_default="NEW",
    )
    assigned_to_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    lost_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


    customer = relationship("Customer", viewonly=True)
    calls = relationship("LeadCall", viewonly=True, order_by="LeadCall.called_at.desc()")


class LeadCall(TimestampMixin, Base):
    __tablename__ = "lead_calls"

    id: Mapped[int] = mapped_column(primary_key=True)
    lead_id: Mapped[int] = mapped_column(ForeignKey("leads.id"))
    called_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    shadow_free_area_sqm: Mapped[float | None] = mapped_column(nullable=True)
    monthly_bill_paise: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    grid_suitable: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    outcome: Mapped[str] = mapped_column(String(255))
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    called_at: Mapped[datetime] = mapped_column(UTCDateTime())
