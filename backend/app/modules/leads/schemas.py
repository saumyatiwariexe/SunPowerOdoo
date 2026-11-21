from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.modules.leads.models import LeadSource, LeadStatus, SystemType


class LeadCallOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    lead_id: int
    called_by_id: int
    shadow_free_area_sqm: float | None
    monthly_bill_paise: int | None
    grid_suitable: bool | None
    outcome: str
    notes: str | None
    called_at: datetime
    created_at: datetime


class LeadCustomer(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    phone: str
    address: str


class LeadOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    customer_id: int
    source: LeadSource
    requested_kw: float
    system_type: SystemType
    subsidy_interest: bool
    status: LeadStatus
    assigned_to_id: int | None
    lost_reason: str | None
    notes: str | None
    created_at: datetime
    updated_at: datetime


class SalesLeadSummary(LeadOut):
    customer: LeadCustomer


class LeadDetail(SalesLeadSummary):
    calls: list[LeadCallOut]


class LeadFields(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source: LeadSource
    requested_kw: float = Field(gt=0, le=100)
    system_type: SystemType
    subsidy_interest: bool = False
    assigned_to_id: int | None = None
    notes: str | None = None


class LeadCreate(LeadFields):
    customer_id: int = Field(gt=0)


class NewCustomerLead(LeadFields):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=120)
    phone: str = Field(pattern=r"^[6-9]\d{9}$")
    address: str = Field(min_length=1)
    pincode: str = Field(pattern=r"^\d{6}$")


class LeadUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source: LeadSource | None = None
    requested_kw: float | None = Field(default=None, gt=0, le=100)
    system_type: SystemType | None = None
    subsidy_interest: bool | None = None
    assigned_to_id: int | None = None
    notes: str | None = None
    status: LeadStatus | None = None


class LeadLostIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    lost_reason: str = Field(min_length=1)

    @field_validator("lost_reason")
    @classmethod
    def reason_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("lost_reason cannot be blank")
        return v.strip()


class LeadCallCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    shadow_free_area_sqm: float | None = Field(default=None, gt=0)
    monthly_bill_paise: int | None = Field(default=None, ge=0)
    grid_suitable: bool | None = None
    outcome: str = Field(min_length=1)
    notes: str | None = None
    called_at: datetime
