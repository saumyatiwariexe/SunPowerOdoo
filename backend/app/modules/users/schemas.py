from typing import Annotated, Self

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator, model_validator

from app.core.money import Paise

from .models import Role


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=254)]
    password: Annotated[str, StringConstraints(min_length=1, max_length=72)]

    @field_validator("email")
    @classmethod
    def normalize_email(cls, email: str) -> str:
        return email.lower()

    @field_validator("password")
    @classmethod
    def validate_password_length(cls, password: str) -> str:
        if len(password.encode("utf-8")) > 72:
            raise ValueError("Password must be 72 bytes or fewer")
        return password


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str
    role: Role
    phone: str | None
    active: bool


StaffName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]
StaffEmail = Annotated[str, StringConstraints(strip_whitespace=True, to_lower=True, max_length=254, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")]
Phone = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=20)]
HourlyRate = Annotated[Paise, Field(le=9_223_372_036_854_775_807)]


class StaffCreate(LoginRequest):
    email: StaffEmail
    name: StaffName
    role: Role
    phone: Phone | None = None
    hourly_rate_paise: HourlyRate = 0
    active: bool = True


class StaffPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: StaffName | None = None
    email: StaffEmail | None = None
    role: Role | None = None
    phone: Phone | None = None
    hourly_rate_paise: HourlyRate | None = None
    active: bool | None = None

    @model_validator(mode="after")
    def validate_changes(self) -> Self:
        for field in self.model_fields_set - {"phone"}:
            if getattr(self, field) is None:
                raise ValueError(f"{field} cannot be null")
        return self


class StaffRead(UserRead):
    hourly_rate_paise: int


class StaffPage(BaseModel):
    data: list[StaffRead]
    meta: dict[str, int]
