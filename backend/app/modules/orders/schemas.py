from datetime import datetime

from pydantic import BaseModel, ConfigDict

from .models import OrderStatus


class OrderRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    number: str
    quote_id: int
    customer_id: int
    status: OrderStatus
    total_paise: int
    advance_min_paise: int
    confirmed_at: datetime | None


class OrderDetailRead(OrderRead):
    paid_paise: int


class OrderPage(BaseModel):
    data: list[OrderRead]
    meta: dict[str, int]
