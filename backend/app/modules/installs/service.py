from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.errors import AppError
from app.core.deps import has_role
from app.core.pagination import Pagination
from app.modules.orders import service as orders
from app.modules.orders.models import OrderStatus
from app.modules.users.models import Role, User, Customer
from app.modules.orders.models import Order

from .models import InstallCrew, InstallJob, InstallStatus, JobPhoto
from .schemas import InstallCompletion, InstallSchedule


def create_for_order(db: Session, order_id: int) -> InstallJob:
    """Create the single job while order confirmation holds the order lock."""
    order = orders.get_order(db, order_id)
    if order.status != OrderStatus.CONFIRMED:
        raise AppError("ORDER_NOT_CONFIRMED", "Confirm the order before creating an install job.", 409)
    job = db.scalar(select(InstallJob).where(InstallJob.order_id == order_id))
    if job is None:
        job = InstallJob(order_id=order_id)
        db.add(job)
        db.flush()
    return job


def get_job(db: Session, job_id: int, *, for_update: bool = False) -> InstallJob:
    job = db.get(InstallJob, job_id, with_for_update=for_update, populate_existing=for_update)
    if job is None:
        raise AppError("INSTALL_NOT_FOUND", "Install job not found.", 404)
    describe_jobs(db, [job])
    return job


def require_member(job: InstallJob, actor: User) -> None:
    if all(member.user_id != actor.id for member in job.crew):
        raise AppError("FORBIDDEN", "You are not assigned to this install job.", 403)


def list_jobs(
    db: Session, paging: Pagination, *, user_id: int | None = None, status: InstallStatus | None = None
) -> tuple[list[InstallJob], int]:
    filters = []
    if user_id is not None:
        filters.append(InstallJob.crew.any(InstallCrew.user_id == user_id))
    if status is not None:
        filters.append(InstallJob.status == status)
    total = db.scalar(select(func.count()).select_from(InstallJob).where(*filters)) or 0
    query = (
        select(InstallJob)
        .where(*filters)
        .options(selectinload(InstallJob.crew), selectinload(InstallJob.photos))
        .order_by(InstallJob.id.desc())
    )
    rows = list(db.scalars(query.offset(paging.offset).limit(paging.page_size)))
    describe_jobs(db, rows)
    return rows, total


def schedule(db: Session, job_id: int, payload: InstallSchedule) -> InstallJob:
    job = get_job(db, job_id, for_update=True)
    if job.status != InstallStatus.SCHEDULED:
        raise AppError("INSTALL_NOT_SCHEDULED", "Only scheduled jobs can be rescheduled.", 409)
    member_ids = {payload.crew_lead_id, *payload.crew_ids}
    current = {member.user_id: member for member in job.crew}
    users = db.scalars(
        select(User).where(User.id.in_(member_ids | current.keys())).order_by(User.id).with_for_update()
    )
    active_crew = {user.id for user in users if user.active and has_role(user, Role.CREW)}
    if not member_ids <= active_crew:
        raise AppError("INVALID_CREW", "Assign only active crew members.", 409)

    conflict = db.scalar(
        select(InstallJob.id)
        .join(InstallCrew, InstallCrew.install_job_id == InstallJob.id)
        .where(
            InstallJob.id != job.id,
            InstallCrew.user_id.in_(member_ids),
            InstallJob.scheduled_start < payload.scheduled_end,
            InstallJob.scheduled_end > payload.scheduled_start,
            InstallJob.status.in_([InstallStatus.SCHEDULED, InstallStatus.IN_PROGRESS]),
        )
        .limit(1)
    )
    if conflict is not None:
        raise AppError("CREW_OVERLAP", "A crew member is already booked during this slot.", 409)

    job.crew_lead_id = payload.crew_lead_id
    job.crew = [current[user_id] if user_id in current else InstallCrew(user_id=user_id) for user_id in sorted(member_ids)]
    job.scheduled_start = payload.scheduled_start
    job.scheduled_end = payload.scheduled_end
    db.flush()
    return job


def start(db: Session, job_id: int, actor: User) -> InstallJob:
    job = get_job(db, job_id, for_update=True)
    require_member(job, actor)
    if job.status != InstallStatus.SCHEDULED:
        raise AppError("INSTALL_NOT_SCHEDULED", "Only scheduled jobs can be started.", 409)
    job.status = InstallStatus.IN_PROGRESS
    job.started_at = datetime.now(UTC)
    db.flush()
    return job


def working_job(db: Session, job_id: int, actor: User) -> InstallJob:
    job = get_job(db, job_id, for_update=True)
    require_member(job, actor)
    if job.status != InstallStatus.IN_PROGRESS:
        raise AppError("INSTALL_NOT_IN_PROGRESS", "Start the job before recording installation proof.", 409)
    return job


def attach_photo(db: Session, job: InstallJob, url: str, caption: str | None) -> JobPhoto:
    photo = JobPhoto(url=url, caption=caption, taken_at=datetime.now(UTC))
    job.photos.append(photo)
    db.flush()
    return photo


def complete(db: Session, job: InstallJob, payload: InstallCompletion, signature_url: str) -> InstallJob:
    if not job.photos:
        raise AppError("INSTALL_PHOTO_REQUIRED", "Upload at least one installation photo.", 409)
    if not signature_url:
        raise AppError("SIGNATURE_REQUIRED", "Record the customer signature.", 409)
    job.started_at = payload.started_at
    job.finished_at = payload.finished_at
    job.system_kw = payload.system_kw
    job.test_notes = payload.test_notes
    job.signed_by_name = payload.signed_by_name
    job.signature_url = signature_url
    job.status = InstallStatus.COMPLETED
    db.flush()
    return job


def accept(db: Session, job_id: int, actor: User) -> InstallJob:
    job = get_job(db, job_id, for_update=True)
    require_member(job, actor)
    if job.status == InstallStatus.ACCEPTED:
        return job
    if job.status != InstallStatus.COMPLETED or not job.signature_url:
        raise AppError("INSTALL_NOT_COMPLETED", "Complete and sign the installation before accepting it.", 409)
    orders.mark_installed(db, job.order_id)
    job.status = InstallStatus.ACCEPTED
    job.accepted_at = datetime.now(UTC)
    db.flush()
    return job


def describe_jobs(db, rows):
    details = {o.id: (o,c) for o,c in db.execute(select(Order, Customer).join(Customer, Customer.id==Order.customer_id).where(Order.id.in_([r.order_id for r in rows])))}
    users = {u.id:u.name for u in db.scalars(select(User).where(User.id.in_({c.user_id for r in rows for c in r.crew})))}
    for row in rows:
        order, customer = details[row.order_id]
        row.order_number = order.number
        row.customer_name, row.customer_phone, row.site_address = customer.name, customer.phone, customer.address
        row.crew_names = ', '.join(users.get(c.user_id, str(c.user_id)) for c in row.crew)
