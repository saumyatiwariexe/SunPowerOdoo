from datetime import datetime
from enum import StrEnum

from sqlalchemy import Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base, TimestampMixin, UTCDateTime


class SurveyStatus(StrEnum):
    SCHEDULED = "SCHEDULED"
    SUBMITTED = "SUBMITTED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class Survey(TimestampMixin, Base):
    __tablename__ = "surveys"

    id: Mapped[int] = mapped_column(primary_key=True)
    lead_id: Mapped[int] = mapped_column(ForeignKey("leads.id"), index=True)
    surveyor_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    scheduled_at: Mapped[datetime] = mapped_column(UTCDateTime())
    roof_direction: Mapped[str | None] = mapped_column(String(40))
    tilt_degrees: Mapped[float | None]
    cable_distance_m: Mapped[float | None]
    shadow_notes: Mapped[str | None] = mapped_column(Text)
    review_note: Mapped[str | None] = mapped_column(Text)
    status: Mapped[SurveyStatus] = mapped_column(
        Enum(SurveyStatus, native_enum=False, create_constraint=True, name="survey_status"),
        default=SurveyStatus.SCHEDULED, server_default="SCHEDULED", index=True,
    )
    approved_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    approved_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    photos: Mapped[list["SurveyPhoto"]] = relationship(
        cascade="all, delete-orphan", order_by="SurveyPhoto.id"
    )


class SurveyPhoto(TimestampMixin, Base):
    __tablename__ = "survey_photos"

    id: Mapped[int] = mapped_column(primary_key=True)
    survey_id: Mapped[int] = mapped_column(ForeignKey("surveys.id", ondelete="CASCADE"), index=True)
    url: Mapped[str] = mapped_column(String(255))
