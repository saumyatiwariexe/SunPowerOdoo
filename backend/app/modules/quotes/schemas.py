from datetime import date
from typing import Annotated, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.core.money import Paise

from .models import QuoteStatus

RecordId = Annotated[int, Field(strict=True, gt=0, le=2_147_483_647)]
MAX_PAISE = 9_223_372_036_854_775_807
Money = Annotated[Paise, Field(le=MAX_PAISE)]


class QuoteCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    lead_id: RecordId
    package_id: RecordId
    valid_until: date
    subsidy_paise: Money = 0


class QuoteLinePatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: RecordId
    qty: Annotated[int, Field(strict=True, gt=0, le=2_147_483_647)]
    unit_price_paise: Money


class QuotePatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    valid_until: date | None = None
    subsidy_paise: Money | None = None
    lines: list[QuoteLinePatch] | None = None

    @model_validator(mode="after")
    def validate_changes(self) -> Self:
        if any(getattr(self, field) is None for field in self.model_fields_set):
            raise ValueError("Quote changes cannot be null")
        if self.lines is not None and len({line.id for line in self.lines}) != len(self.lines):
            raise ValueError("Each quote line may be edited only once")
        return self


class QuoteLineRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    description: str
    qty: int
    unit_price_paise: int
    line_paise: int


class QuoteRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    number: str
    lead_id: int
    customer_id: int
    package_id: int
    status: QuoteStatus
    subtotal_paise: int
    subsidy_paise: int
    total_paise: int
    valid_until: date
    lines: list[QuoteLineRead]


class QuotePage(BaseModel):
    data: list[QuoteRead]
    meta: dict[str, int]
