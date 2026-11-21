from typing import Annotated

from fastapi import APIRouter, Depends, Form, Path, UploadFile
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
from .models import InstallJob, InstallStatus
from .schemas import InstallCompletion, InstallPage, InstallRead, InstallSchedule, PhotoRead

router = APIRouter(prefix="/installs", tags=["installs"])
Db = Annotated[Session, Depends(get_db)]
JobId = Annotated[int, Path(gt=0, le=2_147_483_647)]
Paging = Annotated[Pagination, Depends()]
Crew = Annotated[User, Depends(require_roles("CREW"))]
SchedulingStaff = Annotated[User, Depends(require_roles("DIRECTOR", "SUPPORT"))]
InstallStaff = Annotated[User, Depends(require_roles("DIRECTOR", "SUPPORT", "CREW"))]
AppSettings = Annotated[Settings, Depends(get_settings)]


class InstallCompletionForm(InstallCompletion):
    signature: UploadFile


def _viewable_job(db: Session, job_id: int, actor: User) -> InstallJob:
    job = service.get_job(db, job_id)
    if actor.role == Role.CREW:
        service.require_member(job, actor)
    return job


def _media_url(job_id: int, filename: str) -> str:
    return f"/api/v1/installs/{job_id}/media/{filename}"


@router.get("")
def jobs(db: Db, paging: Paging, actor: SchedulingStaff, status: InstallStatus | None = None) -> InstallPage:
    rows, count = service.list_jobs(db, paging, status=status)
    return InstallPage(data=[InstallRead.model_validate(row) for row in rows], meta=paging.meta(count))


@router.get("/mine")
def mine(db: Db, paging: Paging, actor: Crew, status: InstallStatus | None = None) -> InstallPage:
    rows, count = service.list_jobs(db, paging, user_id=actor.id, status=status)
    return InstallPage(data=[InstallRead.model_validate(row) for row in rows], meta=paging.meta(count))


@router.get("/{job_id}")
def detail(job_id: JobId, db: Db, actor: InstallStaff) -> dict[str, InstallRead]:
    return {"data": InstallRead.model_validate(_viewable_job(db, job_id, actor))}


@router.patch("/{job_id}/schedule")
def schedule(job_id: JobId, payload: InstallSchedule, db: Db, actor: SchedulingStaff) -> dict[str, InstallRead]:
    data = InstallRead.model_validate(service.schedule(db, job_id, payload))
    db.commit()
    return {"data": data}


@router.post("/{job_id}/start")
def start(job_id: JobId, db: Db, actor: Crew) -> dict[str, InstallRead]:
    data = InstallRead.model_validate(service.start(db, job_id, actor))
    db.commit()
    return {"data": data}


@router.post("/{job_id}/photos", status_code=201)
async def photos(
    job_id: JobId, db: Db, actor: Crew, settings: AppSettings,
    file: UploadFile, caption: Annotated[str | None, Form(max_length=255)] = None,
) -> dict[str, PhotoRead]:
    job = service.working_job(db, job_id, actor)
    directory = settings.uploads_dir / "installs"
    filename = await save_image(file, directory)
    try:
        data = PhotoRead.model_validate(service.attach_photo(db, job, _media_url(job_id, filename), caption))
        db.commit()
    except Exception:
        (directory / filename).unlink(missing_ok=True)
        raise
    return {"data": data}


@router.post("/{job_id}/complete")
async def complete(
    job_id: JobId, db: Db, actor: Crew, settings: AppSettings,
    payload: Annotated[InstallCompletionForm, Form(media_type="multipart/form-data")],
) -> dict[str, InstallRead]:
    job = service.working_job(db, job_id, actor)
    directory = settings.uploads_dir / "installs"
    filename = await save_image(payload.signature, directory)
    try:
        data = InstallRead.model_validate(service.complete(db, job, payload, _media_url(job_id, filename)))
        db.commit()
    except Exception:
        (directory / filename).unlink(missing_ok=True)
        raise
    return {"data": data}


@router.post("/{job_id}/accept")
def accept(job_id: JobId, db: Db, actor: Crew) -> dict[str, InstallRead]:
    data = InstallRead.model_validate(service.accept(db, job_id, actor))
    db.commit()
    return {"data": data}


@router.get("/{job_id}/media/{filename}")
def media(
    job_id: JobId,
    filename: Annotated[str, Path(pattern=IMAGE_FILENAME_PATTERN)],
    db: Db,
    actor: InstallStaff,
    settings: AppSettings,
) -> FileResponse:
    job = _viewable_job(db, job_id, actor)
    url = _media_url(job_id, filename)
    file = settings.uploads_dir / "installs" / filename
    if (job.signature_url != url and all(photo.url != url for photo in job.photos)) or not file.is_file():
        raise AppError("INSTALL_MEDIA_NOT_FOUND", "Installation image not found.", 404)
    return FileResponse(file, headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"})
