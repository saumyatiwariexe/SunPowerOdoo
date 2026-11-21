from datetime import datetime
from typing import Annotated, Self

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, StringConstraints, model_validator

from .models import InstallStatus

PositiveId = Annotated[int, Field(strict=True, gt=0, le=2_147_483_647)]


class InstallSchedule(BaseModel):
    model_config = ConfigDict(extra="forbid")

    crew_lead_id: PositiveId
    crew_ids: list[PositiveId] = Field(default_factory=list, max_length=30)
    scheduled_start: AwareDatetime
    scheduled_end: AwareDatetime

    @model_validator(mode="after")
    def check_slot(self) -> Self:
        if self.scheduled_end <= self.scheduled_start:
            raise ValueError("Scheduled end must be after scheduled start")
        return self


class InstallCompletion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    started_at: AwareDatetime
    finished_at: AwareDatetime
    system_kw: Annotated[float, Field(gt=0, allow_inf_nan=False)]
    signed_by_name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]
    test_notes: Annotated[str, StringConstraints(max_length=2000)] | None = None

    @model_validator(mode="after")
    def check_duration(self) -> Self:
        if self.finished_at <= self.started_at:
            raise ValueError("Finish time must be after start time")
        return self


class CrewRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: int


class PhotoRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    url: str
    caption: str | None
    taken_at: datetime


class InstallRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    order_id: int
    crew_lead_id: int | None
    scheduled_start: datetime | None
    scheduled_end: datetime | None
    started_at: datetime | None
    finished_at: datetime | None
    system_kw: float | None
    test_notes: str | None
    status: InstallStatus
    signed_by_name: str | None
    signature_url: str | None
    accepted_at: datetime | None
    crew: list[CrewRead]
    photos: list[PhotoRead]


class InstallPage(BaseModel):
    data: list[InstallRead]
    meta: dict[str, int]
