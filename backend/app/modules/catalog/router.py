from enum import StrEnum
from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import require_roles
from app.core.pagination import Pagination

from . import service
from .schemas import (
    PackageCreate,
    PackagePage,
    PackagePatch,
    PackageRead,
    PackageSummary,
    ProductCreate,
    ProductPage,
    ProductPatch,
    ProductRead,
)

router = APIRouter(tags=["catalog"])
product_reader = Depends(require_roles("DIRECTOR", "SALES", "WAREHOUSE"))
package_reader = Depends(require_roles("DIRECTOR", "SALES"))
catalog_editor = Depends(require_roles("DIRECTOR"))
Db = Annotated[Session, Depends(get_db)]
Paging = Annotated[Pagination, Depends()]
ResourceId = Annotated[int, Path(gt=0, le=2_147_483_647)]
Search = Annotated[str, Query(max_length=120)]


class PackageStatus(StrEnum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


@router.get("/products", dependencies=[product_reader])
def products(db: Db, paging: Paging, q: Search = "") -> ProductPage:
    rows, total = service.list_products(db, paging, q)
    return ProductPage(data=[ProductRead.model_validate(row) for row in rows], meta=paging.meta(total))


@router.get("/products/{product_id}", dependencies=[product_reader])
def product_detail(product_id: ResourceId, db: Db) -> dict[str, ProductRead]:
    return {"data": ProductRead.model_validate(service.get_product(db, product_id))}


@router.post("/products", status_code=201, dependencies=[catalog_editor])
def add_product(payload: ProductCreate, db: Db) -> dict[str, ProductRead]:
    data = ProductRead.model_validate(service.create_product(db, payload))
    db.commit()
    return {"data": data}


@router.patch("/products/{product_id}", dependencies=[catalog_editor])
def edit_product(product_id: ResourceId, payload: ProductPatch, db: Db) -> dict[str, ProductRead]:
    data = ProductRead.model_validate(service.update_product(db, product_id, payload))
    db.commit()
    return {"data": data}


@router.get("/packages", dependencies=[package_reader])
def packages(db: Db, paging: Paging, q: Search = "", status: PackageStatus | None = None) -> PackagePage:
    active = None if status is None else status == PackageStatus.ACTIVE
    rows, total = service.list_packages(db, paging, q, active)
    return PackagePage(data=[PackageSummary.model_validate(row) for row in rows], meta=paging.meta(total))


@router.get("/packages/{package_id}", dependencies=[package_reader])
def package_detail(package_id: ResourceId, db: Db) -> dict[str, PackageRead]:
    return {"data": PackageRead.model_validate(service.get_package(db, package_id))}


@router.post("/packages", status_code=201, dependencies=[catalog_editor])
def add_package(payload: PackageCreate, db: Db) -> dict[str, PackageRead]:
    data = PackageRead.model_validate(service.create_package(db, payload))
    db.commit()
    return {"data": data}


@router.patch("/packages/{package_id}", dependencies=[catalog_editor])
def edit_package(package_id: ResourceId, payload: PackagePatch, db: Db) -> dict[str, PackageRead]:
    data = PackageRead.model_validate(service.update_package(db, package_id, payload))
    db.commit()
    return {"data": data}
