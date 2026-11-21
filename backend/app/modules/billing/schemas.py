from datetime import datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field


class StrictSchema(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)


class PaymentCreateIn(StrictSchema):
    amount_paise: int = Field(..., strict=True, gt=0, le=9_223_372_036_854_775_807)
    method: Literal["CASH", "CARD", "UPI", "BANK"]
    reference: str | None = Field(default=None, max_length=100)


class InvoiceCreateIn(StrictSchema):
    order_id: int
