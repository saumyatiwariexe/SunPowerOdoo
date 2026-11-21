from datetime import date

from pydantic import BaseModel, ConfigDict

from .models import QuoteStatus


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
