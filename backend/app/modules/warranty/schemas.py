from datetime import date
from pydantic import BaseModel, ConfigDict


class WarrantyLookupOut(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    serial_unit_id: int
    serial_no: str
    product_id: int
    product_name: str
    sku: str
    customer_id: int | None
    customer_name: str | None
    customer_phone: str | None
    warranty_id: int | None
    start_date: date | None
    end_date: date | None
    in_warranty: bool
    warranty_status: str