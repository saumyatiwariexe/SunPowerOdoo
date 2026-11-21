from pydantic import BaseModel, ConfigDict, Field, field_validator
from app.modules.users.schemas import LoginRequest, StaffEmail


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
