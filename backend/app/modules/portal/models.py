from datetime import datetime
from sqlalchemy import ForeignKey, String
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
