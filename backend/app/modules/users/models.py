from enum import StrEnum

from sqlalchemy import BigInteger, Boolean, CheckConstraint, Enum, ForeignKey, String, Text, true
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base, TimestampMixin


class Role(StrEnum):
    DIRECTOR = "DIRECTOR"
    SALES = "SALES"
    SURVEYOR = "SURVEYOR"
    WAREHOUSE = "WAREHOUSE"
    CREW = "CREW"
    SUPPORT = "SUPPORT"


class User(TimestampMixin, Base):
    __tablename__ = "users"
    __table_args__ = (CheckConstraint("hourly_rate_paise >= 0", name="ck_users_hourly_rate_paise"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(254), unique=True)
    password_hash: Mapped[str] = mapped_column(String(60))
    role: Mapped[Role] = mapped_column(
        Enum(Role, native_enum=False, create_constraint=True, validate_strings=True, name="user_role")
    )
    phone: Mapped[str | None] = mapped_column(String(20))
    hourly_rate_paise: Mapped[int] = mapped_column(BigInteger, default=0, server_default="0")
    active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true())
    role_grants: Mapped[list["UserRoleGrant"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", lazy="selectin"
    )

    @property
    def additional_roles(self) -> list[Role]:
        return sorted((grant.role for grant in self.role_grants), key=str)


class UserRoleGrant(TimestampMixin, Base):
    __tablename__ = "user_role_grants"
    __table_args__ = (CheckConstraint("role <> 'DIRECTOR'", name="ck_role_grant_no_director"),)

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    role: Mapped[Role] = mapped_column(
        Enum(Role, native_enum=False, create_constraint=True, validate_strings=True, name="grant_role"),
        primary_key=True,
    )
    user: Mapped[User] = relationship(back_populates="role_grants")


class Customer(TimestampMixin, Base):
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    phone: Mapped[str] = mapped_column(String(20), index=True)
    email: Mapped[str | None] = mapped_column(String(254))
    address: Mapped[str] = mapped_column(Text)
    city: Mapped[str | None] = mapped_column(String(120))
    pincode: Mapped[str] = mapped_column(String(6))
