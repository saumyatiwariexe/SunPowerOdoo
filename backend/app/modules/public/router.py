from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.modules.public import service
from app.modules.public.schemas import EnquiryIn, EnquiryOut, PackageComponentPublic, PackagePublic

router = APIRouter(prefix="/public", tags=["public"])


@router.post("/enquiries", response_model=dict, status_code=201)
def submit_enquiry(
    body: EnquiryIn,
    db: Annotated[Session, Depends(get_db)],
) -> dict:
    result = service.create_enquiry(db, body)
    db.commit()
    return {"data": result.model_dump()}


@router.get("/packages", response_model=dict)
def list_packages(
    db: Annotated[Session, Depends(get_db)],
) -> dict:
    packages = service.get_packages_public(db)
    return {
        "data": [
            PackagePublic.model_validate(p).model_copy(update={"components": [
                PackageComponentPublic(product_name=item.product.name, category=item.product.category.value, qty=item.qty)
                for item in p.items
            ]}).model_dump() if hasattr(p, "__table__") else p
            for p in packages
        ]
    }
