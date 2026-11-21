from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class StrictSchema(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)


class ScanSerialIn(StrictSchema):
    serial_no: str = Field(..., min_length=1, max_length=100)


class DispatchIn(StrictSchema):
    vehicle: str | None = Field(default=None, max_length=100)