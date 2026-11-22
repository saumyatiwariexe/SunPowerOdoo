from datetime import datetime
from typing import Annotated

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, StringConstraints

from .models import SurveyStatus

Note = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)]


class SurveySchedule(BaseModel):
    model_config = ConfigDict(extra="forbid")

    surveyor_id: Annotated[int, Field(strict=True, gt=0, le=2_147_483_647)]
    scheduled_at: AwareDatetime


class SurveySubmit(BaseModel):
    model_config = ConfigDict(extra="forbid")

    roof_direction: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=40)]
    tilt_degrees: Annotated[float, Field(ge=0, le=90, allow_inf_nan=False)]
    cable_distance_m: Annotated[float, Field(ge=0, allow_inf_nan=False)]
    shadow_notes: Note | None = None


class SurveyReview(BaseModel):
    model_config = ConfigDict(extra="forbid")

    note: Note


class SurveyPhotoRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    url: str


class SurveyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    customer_name: str | None = None
    customer_phone: str | None = None
    site_address: str | None = None
    surveyor_name: str | None = None

    id: int
    lead_id: int
    surveyor_id: int
    scheduled_at: datetime
    roof_direction: str | None
    tilt_degrees: float | None
    cable_distance_m: float | None
    shadow_notes: str | None
    review_note: str | None
    status: SurveyStatus
    approved_by_id: int | None
    approved_at: datetime | None
    photos: list[SurveyPhotoRead]


class SurveyPage(BaseModel):
    data: list[SurveyRead]
    meta: dict[str, int]
