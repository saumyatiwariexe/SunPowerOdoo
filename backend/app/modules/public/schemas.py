from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class EnquiryIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=120)
    phone: str = Field(min_length=7, max_length=20, pattern=r"^\+?[0-9\s\-()]{7,20}$")
    email: str | None = Field(default=None, max_length=254)
    address: str = Field(min_length=1)
    city: str | None = Field(default=None, max_length=120)
    pincode: str = Field(min_length=6, max_length=6, pattern=r"^\d{6}$")
    requested_kw: float = Field(gt=0, le=100)
    system_type: str = Field(pattern=r"^(ON_GRID|OFF_GRID)$")
    subsidy_interest: bool = False
    monthly_bill_paise: int | None = Field(default=None, ge=0)
    # Honeypot field — must remain empty
    website: str = Field(default="", max_length=0)

    @field_validator("website")
    @classmethod
    def honeypot_must_be_empty(cls, v: str) -> str:
        if v:
            raise ValueError("Bot detected")
        return v


class EnquiryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    lead_id: int
    customer_id: int
    reference: str  # e.g. "LEAD-0001"


class PackageItemPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    product_name: str
    qty: float


class PackagePublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    system_type: str
    capacity_kw: float
    price_paise: int
