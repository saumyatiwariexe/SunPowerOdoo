from typing import Annotated, Self

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, StringConstraints, model_validator

from app.core.money import Paise

from .models import ProductCategory, SystemType

ShortName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]
Sku = Annotated[str, StringConstraints(strip_whitespace=True, to_upper=True, min_length=1, max_length=64)]
Unit = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=24)]
Int32 = Annotated[int, Field(strict=True, ge=0, le=2_147_483_647)]
PositiveInt32 = Annotated[int, Field(strict=True, gt=0, le=2_147_483_647)]
Capacity = Annotated[int, Field(strict=True, ge=1, le=5)]
CatalogPaise = Annotated[Paise, Field(le=9_223_372_036_854_775_807)]


class ProductCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sku: Sku
    name: ShortName
    category: ProductCategory
    unit: Unit
    cost_paise: CatalogPaise
    price_paise: CatalogPaise
    tracks_serial: bool = False
    warranty_months: PositiveInt32 | None = None
    reorder_level: Int32 = 0


class ProductPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sku: Sku | None = None
    name: ShortName | None = None
    category: ProductCategory | None = None
    unit: Unit | None = None
    cost_paise: CatalogPaise | None = None
    price_paise: CatalogPaise | None = None
    tracks_serial: bool | None = None
    warranty_months: PositiveInt32 | None = None
    reorder_level: Int32 | None = None

    @model_validator(mode="after")
    def disallow_nulls(self) -> Self:
        for field in self.model_fields_set - {"warranty_months"}:
            if getattr(self, field) is None:
                raise ValueError(f"{field} cannot be null")
        return self


class ProductRead(ProductCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    on_hand: int


class PackageItemInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    product_id: PositiveInt32
    qty: PositiveInt32


def unique_products(items: list[PackageItemInput]) -> list[PackageItemInput]:
    if len({item.product_id for item in items}) != len(items):
        raise ValueError("Each product may appear only once in a package")
    return items


PackageItems = Annotated[list[PackageItemInput], Field(min_length=1), AfterValidator(unique_products)]


class PackageCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: ShortName
    price_paise: CatalogPaise
    system_type: SystemType | None = None
    capacity_kw: Capacity | None = None
    active: bool = True
    items: PackageItems

    @model_validator(mode="after")
    def require_system_capacity_pair(self) -> Self:
        if (self.system_type is None) != (self.capacity_kw is None):
            raise ValueError("Set both system_type and capacity_kw for a solar system")
        return self


class PackagePatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: ShortName | None = None
    price_paise: CatalogPaise | None = None
    system_type: SystemType | None = None
    capacity_kw: Capacity | None = None
    active: bool | None = None
    items: PackageItems | None = None

    @model_validator(mode="after")
    def disallow_nulls(self) -> Self:
        for field in self.model_fields_set - {"system_type", "capacity_kw"}:
            if getattr(self, field) is None:
                raise ValueError(f"{field} cannot be null")
        return self


class PackageSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    system_type: SystemType | None
    capacity_kw: int | None
    price_paise: int
    active: bool


class PackageItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    product_id: int
    qty: int


class PackageRead(PackageSummary):
    items: list[PackageItemRead]


class ProductPage(BaseModel):
    data: list[ProductRead]
    meta: dict[str, int]


class PackagePage(BaseModel):
    data: list[PackageSummary]
    meta: dict[str, int]
