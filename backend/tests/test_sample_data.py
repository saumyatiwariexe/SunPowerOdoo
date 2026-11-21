from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

import app.models_registry  # noqa: F401
from app.core.db import Base
from app.modules.catalog.models import Package
from app.modules.deliveries.models import Delivery, DeliveryScan
from app.modules.orders.models import Order
from app.modules.quotes.models import Quote
from app.modules.surveys.models import Survey, SurveyStatus
from app.modules.users.models import Customer, Role, User
from app.modules.warranty.models import Warranty
from seed.seed_sample_data import TARGET, add_sample_data


def test_sample_cohort_covers_every_table_and_is_repeatable():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as db, db.begin():
        first = add_sample_data(db, "throwaway-test-password")
        assert len(first) == 29
        assert all(count >= TARGET for count in first.values())

        order = db.scalar(select(Order).where(Order.number == "ORD-SMP-0001"))
        quote = db.get(Quote, order.quote_id)
        survey = db.scalar(select(Survey).where(Survey.lead_id == quote.lead_id))
        delivery = db.scalar(select(Delivery).where(Delivery.order_id == order.id))
        assert survey.status == SurveyStatus.APPROVED
        assert db.get(Package, quote.package_id).active is False
        assert quote.customer_id == order.customer_id
        assert delivery.status == "DELIVERED"
        assert db.scalar(select(func.count()).select_from(DeliveryScan).where(
            DeliveryScan.delivery_id == delivery.id)) == 3
        assert db.scalar(select(func.count()).select_from(Warranty).where(
            Warranty.order_id == order.id)) == 3
        assert db.scalar(select(User).where(User.email == "sample.staff.001@sunpower.invalid")).role == Role.SALES
        assert db.scalar(select(Customer).where(Customer.id == order.customer_id)).email.endswith(".invalid")

        second = add_sample_data(db, "throwaway-test-password")
        assert second == first
    engine.dispose()
