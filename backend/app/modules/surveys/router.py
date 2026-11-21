from typing import Annotated

from fastapi import APIRouter, Depends, Path, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.db import get_db
from app.core.deps import require_roles
from app.core.errors import AppError
from app.core.pagination import Pagination
from app.core.uploads import IMAGE_FILENAME_PATTERN, save_image
from app.modules.users.models import Role, User

from . import service
from .models import Survey, SurveyStatus
from .schemas import SurveyPage, SurveyPhotoRead, SurveyRead, SurveyReview, SurveySchedule, SurveySubmit

router = APIRouter(tags=["surveys"])
Db = Annotated[Session, Depends(get_db)]
RecordId = Annotated[int, Path(gt=0, le=2_147_483_647)]
Paging = Annotated[Pagination, Depends()]
ReviewStaff = Annotated[User, Depends(require_roles("DIRECTOR", "SALES"))]
Surveyor = Annotated[User, Depends(require_roles("SURVEYOR"))]
SurveyStaff = Annotated[User, Depends(require_roles("DIRECTOR", "SALES", "SURVEYOR"))]
AppSettings = Annotated[Settings, Depends(get_settings)]


def _viewable_survey(db: Session, survey_id: int, actor: User) -> Survey:
    result = service.get_survey(db, survey_id)
    if actor.role == Role.SURVEYOR:
        service.require_assigned(result, actor)
    return result


def _photo_url(survey_id: int, filename: str) -> str:
    return f"/api/v1/surveys/{survey_id}/photos/{filename}"


@router.post("/leads/{lead_id}/survey", status_code=201)
def schedule(lead_id: RecordId, payload: SurveySchedule, db: Db, actor: ReviewStaff) -> dict[str, SurveyRead]:
    result = SurveyRead.model_validate(service.schedule(db, lead_id, payload, actor))
    db.commit()
    return {"data": result}


@router.get("/surveys")
def surveys(db: Db, paging: Paging, actor: ReviewStaff, status: SurveyStatus | None = None) -> SurveyPage:
    rows, count = service.list_surveys(db, paging, status=status)
    return SurveyPage(data=[SurveyRead.model_validate(row) for row in rows], meta=paging.meta(count))


@router.get("/surveys/mine")
def my_surveys(db: Db, paging: Paging, actor: Surveyor, status: SurveyStatus | None = None) -> SurveyPage:
    rows, count = service.list_surveys(db, paging, surveyor_id=actor.id, status=status)
    return SurveyPage(data=[SurveyRead.model_validate(row) for row in rows], meta=paging.meta(count))


@router.get("/surveys/{survey_id}")
def survey(survey_id: RecordId, db: Db, actor: SurveyStaff) -> dict[str, SurveyRead]:
    return {"data": SurveyRead.model_validate(_viewable_survey(db, survey_id, actor))}


@router.post("/surveys/{survey_id}/photos", status_code=201)
async def add_photo(
    survey_id: RecordId, file: UploadFile, db: Db, actor: Surveyor, settings: AppSettings,
) -> dict[str, SurveyPhotoRead]:
    survey = service.scheduled_survey(db, survey_id, actor)
    directory = settings.uploads_dir / "surveys"
    filename = await save_image(file, directory)
    try:
        data = SurveyPhotoRead.model_validate(service.attach_photo(db, survey, _photo_url(survey_id, filename)))
        db.commit()
    except Exception:
        (directory / filename).unlink(missing_ok=True)
        raise
    return {"data": data}


@router.get("/surveys/{survey_id}/photos/{filename}")
def photo(
    survey_id: RecordId, filename: Annotated[str, Path(pattern=IMAGE_FILENAME_PATTERN)],
    db: Db, actor: SurveyStaff, settings: AppSettings,
) -> FileResponse:
    survey = _viewable_survey(db, survey_id, actor)
    path = settings.uploads_dir / "surveys" / filename
    url = _photo_url(survey_id, filename)
    if all(photo.url != url for photo in survey.photos) or not path.is_file():
        raise AppError("SURVEY_PHOTO_NOT_FOUND", "Survey photo not found.", 404)
    return FileResponse(path, headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"})


@router.post("/surveys/{survey_id}/submit")
def submit(survey_id: RecordId, payload: SurveySubmit, db: Db, actor: Surveyor) -> dict[str, SurveyRead]:
    result = SurveyRead.model_validate(service.submit(db, survey_id, payload, actor))
    db.commit()
    return {"data": result}


@router.post("/surveys/{survey_id}/approve")
def approve(survey_id: RecordId, payload: SurveyReview, db: Db, actor: ReviewStaff) -> dict[str, SurveyRead]:
    result = SurveyRead.model_validate(service.review(db, survey_id, payload.note, actor, approved=True))
    db.commit()
    return {"data": result}


@router.post("/surveys/{survey_id}/reject")
def reject(survey_id: RecordId, payload: SurveyReview, db: Db, actor: ReviewStaff) -> dict[str, SurveyRead]:
    result = SurveyRead.model_validate(service.review(db, survey_id, payload.note, actor, approved=False))
    db.commit()
    return {"data": result}
