from enum import StrEnum

from sqlalchemy import BigInteger, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, TimestampMixin


class SubsidyStatus(StrEnum):
    NOT_APPLIED = "NOT_APPLIED"
    SUBMITTED = "SUBMITTED"
    APPROVED = "APPROVED"
    PAID = "PAID"
    REJECTED = "REJECTED"


class SubsidyClaim(TimestampMixin, Base):
    __tablename__ = "subsidy_claims"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", use_alter=True, name="fk_subsidy_claims_order_id"))
    scheme: Mapped[str] = mapped_column(String(120))
    status: Mapped[SubsidyStatus] = mapped_column(
        Enum(
            SubsidyStatus,
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
            name="subsidy_status",
        ),
        default=SubsidyStatus.NOT_APPLIED,
        server_default="NOT_APPLIED",
    )
    amount_paise: Mapped[int] = mapped_column(BigInteger, default=0, server_default="0")
    reference_no: Mapped[str | None] = mapped_column(String(120), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
