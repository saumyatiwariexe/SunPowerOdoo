from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.modules.subsidy.models import SubsidyStatus


class SubsidyClaimOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    order_id: int
    order_number: str | None = None
    customer_name: str | None = None
    scheme: str
    status: SubsidyStatus
    amount_paise: int
    reference_no: str | None
    notes: str | None
    created_at: datetime
    updated_at: datetime


class SubsidyClaimUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scheme: str | None = Field(default=None, min_length=1)
    status: SubsidyStatus | None = None
    amount_paise: int | None = Field(default=None, ge=0)
    reference_no: str | None = None
    notes: str | None = None
