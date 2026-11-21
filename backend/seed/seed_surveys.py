from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.leads.models import Lead, LeadStatus
from app.modules.surveys.models import Survey
from app.modules.surveys.schemas import SurveySchedule
from app.modules.surveys.service import schedule
from app.modules.users.models import Customer, User


def seed_surveys(db: Session) -> None:
    """Schedule the seeded pending-survey lead for the demo surveyor."""
    lead = db.scalar(
        select(Lead).join(Customer).where(Customer.phone == "9000012345", Lead.status == LeadStatus.SURVEY_PENDING)
    )
    if lead is None or db.scalar(select(Survey.id).where(Survey.lead_id == lead.id).limit(1)) is not None:
        return

    director = db.scalar(select(User).where(User.email == "director@sunpower.test"))
    surveyor = db.scalar(select(User).where(User.email == "surveyor@sunpower.test"))
    if director is not None and director.active and surveyor is not None and surveyor.active:
        schedule(
            db, lead.id,
            SurveySchedule(surveyor_id=surveyor.id, scheduled_at=datetime.now(UTC) + timedelta(hours=2)),
            director,
        )
