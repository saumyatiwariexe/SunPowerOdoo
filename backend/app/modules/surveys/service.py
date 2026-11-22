from datetime import UTC, datetime

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.errors import AppError
from app.core.deps import has_role
from app.core.pagination import Pagination
from app.modules.leads import service as leads
from app.modules.leads.models import Lead, LeadStatus
from app.modules.leads.schemas import LeadUpdate
from app.modules.users.models import Customer, Role, User, UserRoleGrant

from .models import Survey, SurveyPhoto, SurveyStatus
from .schemas import SurveySchedule, SurveySubmit


def is_approved(db: Session, lead_id: int) -> bool:
    return db.scalar(
        select(Survey.id).where(Survey.lead_id == lead_id, Survey.status == SurveyStatus.APPROVED).limit(1)
    ) is not None


def list_surveys(
    db: Session, paging: Pagination, *, surveyor_id: int | None = None, status: SurveyStatus | None = None
) -> tuple[list[Survey], int]:
    filters = []
    if surveyor_id is not None:
        filters.append(Survey.surveyor_id == surveyor_id)
    if status is not None:
        filters.append(Survey.status == status)
    total = db.scalar(select(func.count()).select_from(Survey).where(*filters)) or 0
    query = (
        select(Survey).where(*filters).options(selectinload(Survey.photos))
        .order_by(Survey.id.desc())
    )
    rows = list(db.scalars(query.offset(paging.offset).limit(paging.page_size)))
    describe_surveys(db, rows)
    return rows, total


def get_survey(db: Session, survey_id: int, *, for_update: bool = False) -> Survey:
    survey = db.get(Survey, survey_id, with_for_update=for_update, populate_existing=for_update)
    if survey is None:
        raise AppError("SURVEY_NOT_FOUND", "Survey not found.", 404)
    describe_surveys(db, [survey])
    return survey


def require_assigned(survey: Survey, actor: User) -> None:
    if survey.surveyor_id != actor.id:
        raise AppError("FORBIDDEN", "This survey is assigned to another surveyor.", 403)


READY_STATUSES = (LeadStatus.CONTACTED, LeadStatus.SURVEY_PENDING)


def scheduling_options(db: Session, lead_id: int | None = None) -> dict:
    active_visit = select(Survey.id).where(Survey.lead_id == Lead.id, Survey.status != SurveyStatus.REJECTED)
    eligible = (
        select(Lead.id, Customer.name, Customer.phone, Lead.requested_kw, Lead.status).join(Customer, Customer.id == Lead.customer_id)
        .where(Lead.status.in_(READY_STATUSES), ~active_visit.exists())
        .order_by(Customer.name, Lead.id)
    )
    existing_id = None
    if lead_id is not None:
        eligible = eligible.where(Lead.id == lead_id)
        existing_id = db.scalar(select(Survey.id).where(
            Survey.lead_id == lead_id, Survey.status != SurveyStatus.REJECTED
        ))
    surveyors = select(User.id, User.name, User.email).where(
        User.active.is_(True),
        or_(User.role == Role.SURVEYOR, User.role_grants.any(UserRoleGrant.role == Role.SURVEYOR)),
    )
    return {
        "leads": [dict(row) for row in db.execute(eligible).mappings()],
        "surveyors": [dict(row) for row in db.execute(surveyors.order_by(User.name, User.id)).mappings()],
        "existing_survey_id": existing_id,
    }


def schedule(db: Session, lead_id: int, payload: SurveySchedule, actor: User) -> Survey:
    lead = leads.get_lead(db, lead_id)
    db.refresh(lead, with_for_update=True)
    if lead.status not in READY_STATUSES:
        message = ("Log the first customer call in the lead inbox before scheduling a survey."
                   if lead.status == LeadStatus.NEW else
                   f"This lead is marked {lead.status.value.replace('_', ' ').lower()} and cannot be scheduled.")
        raise AppError("LEAD_NOT_READY_FOR_SURVEY", message, 409)
    current = db.scalar(
        select(Survey.id).where(Survey.lead_id == lead_id, Survey.status != SurveyStatus.REJECTED).limit(1)
    )
    if current is not None:
        raise AppError("SURVEY_EXISTS", "This lead already has a survey in progress.", 409)
    surveyor = db.get(User, payload.surveyor_id)
    if surveyor is None or not surveyor.active or not has_role(surveyor, Role.SURVEYOR):
        raise AppError("INVALID_SURVEYOR", "Select an active surveyor.", 409)

    if lead.status == LeadStatus.CONTACTED:
        leads.request_survey(db, lead.id, actor)
    survey = Survey(lead_id=lead.id, surveyor_id=surveyor.id, scheduled_at=payload.scheduled_at)
    db.add(survey)
    db.flush()
    return survey


def scheduled_survey(db: Session, survey_id: int, actor: User) -> Survey:
    survey = get_survey(db, survey_id, for_update=True)
    require_assigned(survey, actor)
    if survey.status != SurveyStatus.SCHEDULED:
        raise AppError("SURVEY_NOT_SCHEDULED", "Only a scheduled survey can be updated.", 409)
    return survey


def attach_photo(db: Session, survey: Survey, url: str) -> SurveyPhoto:
    photo = SurveyPhoto(url=url)
    survey.photos.append(photo)
    db.flush()
    return photo


def submit(db: Session, survey_id: int, payload: SurveySubmit, actor: User) -> Survey:
    survey = scheduled_survey(db, survey_id, actor)
    survey.roof_direction = payload.roof_direction
    survey.tilt_degrees = payload.tilt_degrees
    survey.cable_distance_m = payload.cable_distance_m
    survey.shadow_notes = payload.shadow_notes
    survey.status = SurveyStatus.SUBMITTED
    db.flush()
    return survey


def review(db: Session, survey_id: int, note: str, actor: User, *, approved: bool) -> Survey:
    survey = get_survey(db, survey_id, for_update=True)
    if survey.status != SurveyStatus.SUBMITTED:
        raise AppError("SURVEY_NOT_SUBMITTED", "Only a submitted survey can be reviewed.", 409)
    survey.review_note = note
    if approved:
        lead = leads.get_lead(db, survey.lead_id)
        db.refresh(lead, with_for_update=True)
        leads.update_lead(db, lead.id, LeadUpdate(status=LeadStatus.SURVEY_DONE), actor)
        survey.status = SurveyStatus.APPROVED
        survey.approved_at = datetime.now(UTC)
        survey.approved_by_id = actor.id
    else:
        survey.status = SurveyStatus.REJECTED
    db.flush()
    return survey


def describe_surveys(db, rows):
    customers = {lead.id:customer for lead,customer in db.execute(select(Lead, Customer).join(Customer, Customer.id==Lead.customer_id).where(Lead.id.in_([r.lead_id for r in rows])))}
    users = {u.id:u.name for u in db.scalars(select(User).where(User.id.in_([r.surveyor_id for r in rows])))}
    for row in rows:
        customer = customers[row.lead_id]
        row.customer_name, row.customer_phone, row.site_address = customer.name, customer.phone, customer.address
        row.surveyor_name = users.get(row.surveyor_id)
