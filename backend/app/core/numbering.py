from enum import StrEnum

from sqlalchemy import String, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from .db import Base, TimestampMixin
from .errors import AppError


class NumberPrefix(StrEnum):
    QUOTE = "QT"
    ORDER = "ORD"
    INVOICE = "INV"
    TICKET = "TKT"


class Counter(TimestampMixin, Base):
    __tablename__ = "counters"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(16), unique=True)
    value: Mapped[int] = mapped_column(default=0, server_default="0")


def seed_counters(db: Session) -> None:
    existing = set(db.scalars(select(Counter.name)))
    db.add_all(Counter(name=prefix) for prefix in NumberPrefix if prefix not in existing)
    db.flush()


def next_number(db: Session, prefix: NumberPrefix | str) -> str:
    prefix = NumberPrefix(prefix)
    counter = db.scalar(
        select(Counter)
        .where(Counter.name == prefix)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if counter is None:
        raise AppError("COUNTER_NOT_INITIALIZED", "Run the database seed before issuing numbers.", 503)
    counter.value += 1
    db.flush()
    return f"{prefix}-{counter.value:04d}"
