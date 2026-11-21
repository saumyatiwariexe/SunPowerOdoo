from datetime import datetime
from enum import StrEnum

from sqlalchemy import Enum, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base, TimestampMixin, UTCDateTime


class InstallStatus(StrEnum):
    SCHEDULED = "SCHEDULED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    ACCEPTED = "ACCEPTED"


class InstallJob(TimestampMixin, Base):
    __tablename__ = "install_jobs"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), unique=True)
    crew_lead_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True)
    scheduled_start: Mapped[datetime | None] = mapped_column(UTCDateTime())
    scheduled_end: Mapped[datetime | None] = mapped_column(UTCDateTime())
    started_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    finished_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    system_kw: Mapped[float | None]
    test_notes: Mapped[str | None] = mapped_column(Text)
    status: Mapped[InstallStatus] = mapped_column(
        Enum(InstallStatus, native_enum=False, create_constraint=True, name="install_status"),
        default=InstallStatus.SCHEDULED, server_default="SCHEDULED", index=True,
    )
    signed_by_name: Mapped[str | None] = mapped_column(String(120))
    signature_url: Mapped[str | None] = mapped_column(String(255))
    accepted_at: Mapped[datetime | None] = mapped_column(UTCDateTime())

    crew: Mapped[list["InstallCrew"]] = relationship(cascade="all, delete-orphan", order_by="InstallCrew.user_id")
    photos: Mapped[list["JobPhoto"]] = relationship(cascade="all, delete-orphan", order_by="JobPhoto.id")


class InstallCrew(TimestampMixin, Base):
    __tablename__ = "install_crew"
    __table_args__ = (UniqueConstraint("install_job_id", "user_id", name="uq_install_crew_job_user"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    install_job_id: Mapped[int] = mapped_column(ForeignKey("install_jobs.id", ondelete="CASCADE"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)


class JobPhoto(TimestampMixin, Base):
    __tablename__ = "job_photos"

    id: Mapped[int] = mapped_column(primary_key=True)
    install_job_id: Mapped[int] = mapped_column(ForeignKey("install_jobs.id", ondelete="CASCADE"), index=True)
    url: Mapped[str] = mapped_column(String(255))
    caption: Mapped[str | None] = mapped_column(String(255))
    taken_at: Mapped[datetime] = mapped_column(UTCDateTime())
