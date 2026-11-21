from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import require_roles
from app.modules.reports import service
from app.modules.reports.schemas import ProfitJobOut, SummaryOut, TechHoursOut, UnfinishedOut
from app.modules.users.models import Role, User

router = APIRouter(prefix="/reports", tags=["reports"])

DirectorOnly = require_roles(Role.DIRECTOR)


@router.get("/summary", response_model=dict)
def get_summary(
    db: Annotated[Session, Depends(get_db)],
    actor: Annotated[User, Depends(DirectorOnly)],
    range: str = "today",
) -> dict:
    if range not in ("today", "week", "month"):
        range = "today"
    return {"data": service.summary(db, range_=range).model_dump()}


@router.get("/profit-per-job", response_model=dict)
def get_profit_per_job(
    db: Annotated[Session, Depends(get_db)],
    actor: Annotated[User, Depends(DirectorOnly)],
) -> dict:
    return {"data": [r.model_dump() for r in service.profit_per_job(db)]}


@router.get("/unfinished", response_model=dict)
def get_unfinished(
    db: Annotated[Session, Depends(get_db)],
    actor: Annotated[User, Depends(DirectorOnly)],
) -> dict:
    return {"data": service.unfinished(db).model_dump()}


@router.get("/technician-hours", response_model=dict)
def get_technician_hours(
    db: Annotated[Session, Depends(get_db)],
    actor: Annotated[User, Depends(DirectorOnly)],
    month: str | None = None,
) -> dict:
    return {"data": [r.model_dump() for r in service.technician_hours(db, month=month)]}


@router.get("/export.csv")
def export_csv(
    db: Annotated[Session, Depends(get_db)],
    actor: Annotated[User, Depends(DirectorOnly)],
    range: str = "month",
) -> Response:
    csv_content = service.export_csv(db, range_=range)
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=sunpower-report.csv"},
    )
