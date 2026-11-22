from pydantic import BaseModel, ConfigDict, Field, field_validator
from app.modules.users.schemas import LoginRequest, StaffEmail
from typing import Literal


class InviteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: StaffEmail


class CustomerLogin(LoginRequest):
    email: StaffEmail


class ActivateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    token: str = Field(min_length=32, max_length=128)
    password: str = Field(min_length=10, max_length=72)

    @field_validator("password")
    @classmethod
    def password_bytes(cls, value):
        if len(value.encode("utf-8")) > 72:
            raise ValueError("Password must be 72 bytes or fewer")
        return value


class ServiceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    serial_no: str = Field(min_length=1, max_length=100)
    description: str = Field(min_length=10, max_length=2000)


class AcceptQuote(BaseModel):
    model_config = ConfigDict(extra="forbid")
    accepted: Literal[True]


class PaymentReportRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    amount_paise: int = Field(strict=True, gt=0, le=9_007_199_254_740_991)
    method: Literal["UPI", "BANK"]
    reference: str = Field(min_length=3, max_length=100)

    @field_validator("reference")
    @classmethod
    def normalize_reference(cls, value):
        return value.upper()


class PaymentReview(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    decision: Literal["VERIFIED", "REJECTED"]
    note: str = Field(min_length=3, max_length=500)
