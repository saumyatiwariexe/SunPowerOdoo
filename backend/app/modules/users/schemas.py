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
    additional_roles: list[Role]
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
    additional_roles: list[Role] = Field(default_factory=list)
    phone: Phone | None = None
    hourly_rate_paise: HourlyRate = 0
    active: bool = True

    @model_validator(mode="after")
    def validate_grants(self) -> Self:
        validate_role_grants(self.additional_roles, self.role)
        return self


class StaffPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: StaffName | None = None
    email: StaffEmail | None = None
    role: Role | None = None
    additional_roles: list[Role] | None = None
    phone: Phone | None = None
    hourly_rate_paise: HourlyRate | None = None
    active: bool | None = None

    @model_validator(mode="after")
    def validate_changes(self) -> Self:
        for field in self.model_fields_set - {"phone"}:
            if getattr(self, field) is None:
                raise ValueError(f"{field} cannot be null")
        if self.additional_roles is not None:
            validate_role_grants(self.additional_roles, self.role)
        return self


def validate_role_grants(grants: list[Role], primary: Role | None) -> None:
    if Role.DIRECTOR in grants:
        raise ValueError("Director access cannot be granted as an extra role")
    if len(grants) != len(set(grants)):
        raise ValueError("Extra roles must be unique")
    if primary in grants:
        raise ValueError("The primary role cannot also be an extra role")
    if primary == Role.DIRECTOR and grants:
        raise ValueError("Director accounts do not need extra roles")


class StaffRead(UserRead):
    hourly_rate_paise: int


class StaffPage(BaseModel):
    data: list[StaffRead]
    meta: dict[str, int]
