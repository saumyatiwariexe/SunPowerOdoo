"""
test_r1_lead_lost.py

R1: A lead can only be marked LOST when a lost_reason is provided.
    A lead is never deleted — the DELETE endpoint must not exist.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session

from app.core.db import Base
import app.models_registry  # noqa: F401 — registers all models

from app.core.numbering import seed_counters
from app.core.security import hash_password
from app.modules.leads.models import Lead, LeadSource, LeadStatus, SystemType
from app.modules.leads.service import mark_lost, create_lead
from app.modules.leads.schemas import LeadCreate, LeadLostIn
from app.modules.users.models import Customer, Role, User


@pytest.fixture(scope="module")
def engine():
    eng = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    # SQLite doesn't enforce FK by default
    @event.listens_for(eng, "connect")
    def set_fk(dbapi_conn, _):
        dbapi_conn.execute("PRAGMA foreign_keys=ON")
    Base.metadata.create_all(eng)
    yield eng
    Base.metadata.drop_all(eng)


@pytest.fixture()
def db(engine):
    with Session(engine) as session:
        seed_counters(session)
        session.commit()
        yield session
        session.rollback()


@pytest.fixture()
def actor(db):
    user = User(
        name="Sales Demo",
        email="sales_test@sunpower.test",
        password_hash=hash_password("test"),
        role=Role.SALES,
    )
    db.add(user)
    db.flush()
    return user


@pytest.fixture()
def customer(db):
    c = Customer(name="Test Customer", phone="9999999999", address="Test Addr", pincode="560001")
    db.add(c)
    db.flush()
    return c


@pytest.fixture()
def lead(db, actor, customer):
    return create_lead(
        db,
        LeadCreate(
            customer_id=customer.id,
            source=LeadSource.WEB,
            requested_kw=3.0,
            system_type=SystemType.ON_GRID,
        ),
        actor,
    )


class TestR1LeadLost:
    def test_mark_lost_requires_reason(self, db, lead, actor):
        """R1: cannot mark LOST without a reason."""
        from app.core.errors import AppError

        with pytest.raises(AppError) as exc_info:
            mark_lost(db, lead.id, LeadLostIn(lost_reason=""), actor)
        assert exc_info.value.status in (409, 422)

    def test_mark_lost_with_reason_succeeds(self, db, lead, actor):
        """R1: can mark LOST when reason is provided."""
        result = mark_lost(db, lead.id, LeadLostIn(lost_reason="Price too high"), actor)
        assert result.status == LeadStatus.LOST
        assert result.lost_reason == "Price too high"

    def test_cannot_mark_lost_twice(self, db, lead, actor):
        """Cannot mark an already-LOST lead as LOST again."""
        from app.core.errors import AppError

        mark_lost(db, lead.id, LeadLostIn(lost_reason="First reason"), actor)
        with pytest.raises(AppError) as exc_info:
            mark_lost(db, lead.id, LeadLostIn(lost_reason="Second reason"), actor)
        assert exc_info.value.status == 409

    def test_delete_endpoint_does_not_exist(self):
        """R1: There is no DELETE /leads/:id endpoint."""
        from app.modules.leads.router import router

        delete_routes = [
            route for route in router.routes if "DELETE" in getattr(route, "methods", set())
        ]
        assert len(delete_routes) == 0, "DELETE routes found on leads router — R1 violation!"

    def test_lost_reason_blank_string_rejected(self, db, lead, actor):
        """lost_reason of whitespace only should be rejected by validator."""
        with pytest.raises(Exception):  # Pydantic ValidationError or AppError
            mark_lost(db, lead.id, LeadLostIn(lost_reason="   "), actor)
