from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class StrictSchema(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)


class StockReceiveIn(StrictSchema):
    product_id: int
    qty: int = Field(..., strict=True, gt=0, le=2_147_483_647)
    purchase_cost_paise: int = Field(..., strict=True, ge=0, le=9_223_372_036_854_775_807)
    serial_numbers: list[str] = Field(default_factory=list)


class ProductStockOut(StrictSchema):
    id: int
    sku: str
    name: str
    category: str
    unit: str
    tracks_serial: bool
    on_hand: int
    reorder_level: int
    low_stock: bool
    cost_paise: int
    price_paise: int


class SerialUnitOut(StrictSchema):
    id: int
    product_id: int
    serial_no: str
    status: str
    purchase_cost_paise: int
    delivery_id: int | None
    customer_id: int | None
    installed_at: datetime | None
