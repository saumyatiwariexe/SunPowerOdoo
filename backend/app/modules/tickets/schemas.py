from datetime import datetime
from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from app.core.money import Paise

from .models import TicketLineType, TicketPriority, TicketStatus

RecordId = Annotated[int, Field(strict=True, gt=0, le=2_147_483_647)]
Note = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)]
MAX_PAISE = 9_223_372_036_854_775_807


class TicketCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    serial_no: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
    fault_code: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=64)]
    description: Note
    priority: TicketPriority = TicketPriority.NORMAL
    assigned_to_id: RecordId | None = None


class TicketPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    description: Note | None = None
    fault_code: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=64)] | None = None
    assigned_to_id: RecordId | None = None
    priority: TicketPriority | None = None
    status: Literal[TicketStatus.IN_PROGRESS] | None = None

    @model_validator(mode="after")
    def check_nulls(self) -> Self:
        if any(getattr(self, field) is None for field in self.model_fields_set - {"assigned_to_id"}):
            raise ValueError("Status and priority cannot be null")
        return self


class TicketLineCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: TicketLineType
    product_id: RecordId | None = None
    description: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)]
    qty: Annotated[int, Field(strict=True, gt=0, le=2_147_483_647)]
    unit_price_paise: Annotated[Paise, Field(le=MAX_PAISE)]


class TicketResolve(BaseModel):
    model_config = ConfigDict(extra="forbid")

    resolution: Note


class TicketLineRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    type: TicketLineType
    product_id: int | None
    description: str
    qty: int
    unit_price_paise: int


class TicketRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    customer_name: str | None = None
    customer_phone: str | None = None
    serial_no: str | None = None
    assigned_to_name: str | None = None

    id: int
    number: str
    customer_id: int
    serial_unit_id: int
    warranty_id: int | None
    fault_code: str
    description: str
    priority: TicketPriority
    status: TicketStatus
    assigned_to_id: int | None
    resolution: str | None
    customer_confirmed_at: datetime | None
    billable: bool
    lines: list[TicketLineRead]


class TicketClosure(BaseModel):
    ticket: TicketRead
    invoice_id: int | None


class TicketPage(BaseModel):
    data: list[TicketRead]
    meta: dict[str, int]
