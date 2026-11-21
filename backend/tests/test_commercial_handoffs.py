from datetime import UTC, datetime, timedelta
import sys
from types import ModuleType, SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Column, Integer, MetaData, Table, create_engine, event, func, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

import app.models_registry  # noqa: F401
from app.core import db as db_module
from app.core.config import Settings, get_settings
from app.core.deps import get_current_user
from app.core.errors import AppError
from app.core.numbering import seed_counters
from app.main import create_app
from app.modules.catalog.models import Package
from app.modules.installs import service as installs
from app.modules.installs.models import InstallJob, InstallStatus
from app.modules.leads.models import Lead, LeadSource, LeadStatus, SystemType
from app.modules.orders import service as orders
from app.modules.orders.models import Order, OrderStatus
from app.modules.quotes.models import Quote, QuoteStatus
from app.modules.quotes.service import convert_to_order
from app.modules.users.models import Customer, Role, User
from seed.seed_catalog import seed_catalog

API = "/api/v1"
PNG = b"\x89PNG\r\n\x1a\n"


@pytest.fixture
def workspace(monkeypatch, tmp_path):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, _):
        connection.execute("PRAGMA foreign_keys=ON")

    db_module.Base.metadata.create_all(engine)
    metadata = MetaData()
    payments = Table(
        "test_payments", metadata, Column("id", Integer, primary_key=True),
        Column("order_id", Integer, nullable=False), Column("amount_paise", Integer, nullable=False),
    )
    deliveries = Table(
        "test_deliveries", metadata, Column("order_id", Integer, primary_key=True),
    )
    metadata.create_all(engine)
    billing = ModuleType("app.modules.billing.models")
    billing.Payment = SimpleNamespace(order_id=payments.c.order_id, amount_paise=payments.c.amount_paise)
    delivery_api = ModuleType("app.modules.deliveries.service")
    delivery_api.create_for_order = lambda db, order_id: db.execute(deliveries.insert().values(order_id=order_id))
    monkeypatch.setitem(sys.modules, billing.__name__, billing)
    monkeypatch.setitem(sys.modules, delivery_api.__name__, delivery_api)
    monkeypatch.setattr(db_module, "get_engine", lambda: engine)
    settings = Settings(advance_percent=30, uploads_dir=tmp_path)
    monkeypatch.setattr(orders, "get_settings", lambda: settings)

    with Session(engine) as db:
        actors = {}
        for key, role in (
            ("director", Role.DIRECTOR), ("surveyor", Role.SURVEYOR),
            ("other_surveyor", Role.SURVEYOR), ("crew", Role.CREW), ("other_crew", Role.CREW),
        ):
            user = User(name=key, role=role, email=f"{key}@sunpower.test", password_hash="unused")
            db.add(user)
            db.flush()
            actors[key] = User(id=user.id, role=role)
        customer = Customer(name="Customer", address="Test", phone="9999999999", pincode="560001")
        db.add(customer)
        db.flush()
        lead = Lead(
            customer_id=customer.id, source=LeadSource.CALL, requested_kw=3,
            system_type=SystemType.ON_GRID, status=LeadStatus.CONTACTED,
        )
        db.add(lead)
        seed_counters(db)
        seed_catalog(db)
        package_id = db.scalar(select(Package.id).where(Package.name == "On-Grid 3 kW"))
        lead_id = lead.id
        db.commit()

    app = create_app()
    state = SimpleNamespace(actor=actors["director"])
    app.dependency_overrides[get_current_user] = lambda: state.actor
    app.dependency_overrides[get_settings] = lambda: settings
    with TestClient(app) as client:
        yield SimpleNamespace(
            engine=engine, payments=payments, deliveries=deliveries, client=client,
            state=state, actors=actors, lead_id=lead_id, package_id=package_id, uploads_dir=tmp_path,
        )
    engine.dispose()


def test_r2_and_r3_real_survey_approval_then_package_quote(workspace):
    stage = workspace
    client = stage.client
    valid_until = (datetime.now(UTC).date() + timedelta(days=10)).isoformat()
    payload = {"lead_id": stage.lead_id, "package_id": stage.package_id, "valid_until": valid_until}
    blocked = client.post(f"{API}/quotes", json=payload)
    assert blocked.status_code == 409
    assert blocked.json()["error"]["code"] == "SURVEY_NOT_APPROVED"

    survey = client.post(
        f"{API}/leads/{stage.lead_id}/survey",
        json={"surveyor_id": stage.actors["surveyor"].id, "scheduled_at": datetime.now(UTC).isoformat()},
    )
    assert survey.status_code == 201, survey.text
    survey_id = survey.json()["data"]["id"]
    findings = {"roof_direction": "South", "tilt_degrees": 24, "cable_distance_m": 12}
    stage.state.actor = stage.actors["other_surveyor"]
    assert client.post(f"{API}/surveys/{survey_id}/submit", json=findings).status_code == 403
    stage.state.actor = stage.actors["surveyor"]
    assert client.get(f"{API}/surveys/mine").json()["data"][0]["id"] == survey_id
    photo = client.post(
        f"{API}/surveys/{survey_id}/photos", files={"file": ("roof.png", PNG, "image/png")}
    )
    assert photo.status_code == 201, photo.text
    photo_url = photo.json()["data"]["url"]
    assert client.post(f"{API}/surveys/{survey_id}/submit", json=findings).json()["data"]["status"] == "SUBMITTED"
    stage.state.actor = stage.actors["director"]
    assert client.post(f"{API}/quotes", json=payload).status_code == 409
    approved = client.post(f"{API}/surveys/{survey_id}/approve", json={"note": "Roof is suitable."})
    assert approved.status_code == 200, approved.text
    assert approved.json()["data"]["status"] == "APPROVED"
    assert approved.json()["data"]["photos"][0]["url"] == photo_url
    assert client.get(photo_url).content == PNG
    assert client.post(f"{API}/quotes", json={**payload, "lines": []}).status_code == 400

    response = client.post(f"{API}/quotes", json={**payload, "subsidy_paise": 100})
    assert response.status_code == 201, response.text
    quote = response.json()["data"]
    assert quote["number"] == "QT-0001"
    assert quote["status"] == "DRAFT"
    expected = client.get(f"{API}/packages/{stage.package_id}").json()["data"]["items"]
    assert [(row["product_id"], row["qty"]) for row in quote["lines"]] == [
        (row["product_id"], row["qty"]) for row in expected
    ]
    assert {row["description"] for row in quote["lines"]} >= {"Installation service"}
    assert quote["total_paise"] == sum(line["line_paise"] for line in quote["lines"]) - 100
    assert client.get(f"{API}/quotes", params={"q": "QT-0001", "status": "DRAFT"}).json()["meta"]["total"] == 1
    quote_url = f"{API}/quotes/{quote['id']}"
    first = quote["lines"][0]
    change = {"id": first["id"], "qty": first["qty"] + 1, "unit_price_paise": first["unit_price_paise"]}
    edited = client.patch(quote_url, json={"lines": [change]})
    assert edited.status_code == 200, edited.text
    assert edited.json()["data"]["total_paise"] == quote["total_paise"] + first["unit_price_paise"]
    assert client.patch(quote_url, json={"subsidy_paise": 9_000_000_000}).status_code == 409
    assert client.get(quote_url).json()["data"] == edited.json()["data"]
    with Session(stage.engine) as db:
        assert db.get(Lead, stage.lead_id).status == LeadStatus.QUOTED


def add_order(stage, quote_number):
    with Session(stage.engine) as db:
        lead = db.get(Lead, stage.lead_id)
        quote = Quote(
            number=quote_number, lead_id=lead.id, customer_id=lead.customer_id, package_id=stage.package_id,
            subtotal_paise=101, total_paise=101, status=QuoteStatus.ACCEPTED,
            valid_until=datetime.now(UTC).date() + timedelta(days=1),
        )
        db.add(quote)
        db.flush()
        order_id = convert_to_order(db, quote.id).id
        db.commit()
        return order_id


def record_advance(stage, order_id, paise):
    with stage.engine.begin() as connection:
        connection.execute(stage.payments.insert().values(order_id=order_id, amount_paise=paise))


def test_r4_and_r5_confirm_at_exact_threshold_once(workspace):
    stage = workspace
    order_id = add_order(stage, "QT-TEST-1")
    record_advance(stage, order_id, 30)
    url = f"{API}/orders/{order_id}/confirm"
    blocked = stage.client.post(url)
    assert blocked.status_code == 409
    assert blocked.json()["error"]["code"] == "ADVANCE_REQUIRED"
    with Session(stage.engine) as db:
        assert db.get(Order, order_id).status == OrderStatus.DRAFT
        assert db.scalar(select(InstallJob.id)) is None
        assert db.scalar(select(stage.deliveries.c.order_id)) is None

    record_advance(stage, order_id, 1)
    confirmed = stage.client.post(url)
    assert confirmed.status_code == 200, confirmed.text
    assert confirmed.json()["data"]["status"] == "CONFIRMED"
    assert confirmed.json()["data"]["confirmed_at"]
    assert stage.client.post(url).json()["data"] == confirmed.json()["data"]
    with Session(stage.engine) as db:
        assert db.scalar(select(func.count()).select_from(InstallJob)) == 1
        assert db.scalar(select(func.count()).select_from(stage.deliveries)) == 1


def test_r5_failure_rolls_back_delivery_job_and_confirmation(workspace, monkeypatch):
    stage = workspace
    order_id = add_order(stage, "QT-TEST-2")
    record_advance(stage, order_id, 31)
    create_for_order = installs.create_for_order

    def fail_after_job(db, order_id):
        create_for_order(db, order_id)
        raise AppError("TEST_INSTALL_FAILURE", "Simulate failure later in the job setup.", 409)

    monkeypatch.setattr(installs, "create_for_order", fail_after_job)
    assert stage.client.post(f"{API}/orders/{order_id}/confirm").status_code == 409
    with Session(stage.engine) as db:
        order = db.get(Order, order_id)
        assert order.status == OrderStatus.DRAFT and order.confirmed_at is None
        assert db.scalar(select(InstallJob.id)) is None
        assert db.scalar(select(stage.deliveries.c.order_id)) is None


def confirmed_job(stage, quote_number):
    order_id = add_order(stage, quote_number)
    record_advance(stage, order_id, 31)
    response = stage.client.post(f"{API}/orders/{order_id}/confirm")
    assert response.status_code == 200, response.text
    with Session(stage.engine) as db:
        return db.scalar(select(InstallJob.id).where(InstallJob.order_id == order_id)), order_id


def schedule_data(stage, start, end):
    return {
        "crew_lead_id": stage.actors["crew"].id, "crew_ids": [stage.actors["other_crew"].id],
        "scheduled_start": start.isoformat(), "scheduled_end": end.isoformat(),
    }


def test_r13_checks_all_crew_members_and_allows_adjacent_slots(workspace):
    stage = workspace
    first, _ = confirmed_job(stage, "QT-SLOT-1")
    second, _ = confirmed_job(stage, "QT-SLOT-2")
    start = datetime.now(UTC)
    end = start + timedelta(hours=2)
    response = stage.client.patch(f"{API}/installs/{first}/schedule", json=schedule_data(stage, start, end))
    assert response.status_code == 200, response.text
    url = f"{API}/installs/{second}/schedule"
    overlap = {
        **schedule_data(stage, start + timedelta(hours=1), end + timedelta(hours=1)),
        "crew_lead_id": stage.actors["other_crew"].id, "crew_ids": [],
    }
    conflict = stage.client.patch(url, json=overlap)
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "CREW_OVERLAP"
    assert stage.client.patch(url, json=schedule_data(stage, end, end + timedelta(hours=1))).status_code == 200


def test_r12_requires_photo_signature_and_valid_times(workspace):
    stage = workspace
    job_id, order_id = confirmed_job(stage, "QT-PROOF")
    root = f"{API}/installs/{job_id}"
    now = datetime.now(UTC)
    slot = schedule_data(stage, now, now + timedelta(hours=2))
    assert stage.client.patch(f"{root}/schedule", json=slot).status_code == 200
    stage.state.actor = stage.actors["crew"]
    assert stage.client.post(f"{root}/start").status_code == 200
    proof = {
        "started_at": now.isoformat(), "finished_at": (now + timedelta(hours=1)).isoformat(),
        "system_kw": "3", "signed_by_name": "Customer",
    }
    signature = {"signature": ("signature.png", PNG, "image/png")}
    assert stage.client.post(f"{root}/complete", data=proof).status_code == 400
    no_photo = stage.client.post(f"{root}/complete", data=proof, files=signature)
    assert no_photo.status_code == 409, no_photo.text
    assert no_photo.json()["error"]["code"] == "INSTALL_PHOTO_REQUIRED"
    assert not list((stage.uploads_dir / "installs").glob("*.png"))
    photo = stage.client.post(f"{root}/photos", files={"file": ("roof.png", PNG, "image/png")})
    assert photo.status_code == 201, photo.text
    assert stage.client.get(photo.json()["data"]["url"]).content == PNG
    bad_times = {**proof, "finished_at": now.isoformat()}
    assert stage.client.post(f"{root}/complete", data=bad_times, files=signature).status_code == 400
    finished = stage.client.post(f"{root}/complete", data=proof, files=signature)
    assert finished.status_code == 200, finished.text
    assert finished.json()["data"]["status"] == "COMPLETED"
    assert stage.client.get(finished.json()["data"]["signature_url"]).content == PNG
    assert stage.client.post(f"{root}/accept").status_code == 409
    with Session(stage.engine) as db:
        db.get(Order, order_id).status = OrderStatus.DISPATCHED
        db.commit()
    assert stage.client.post(f"{root}/accept").json()["data"]["status"] == "ACCEPTED"
    with Session(stage.engine) as db:
        assert db.get(InstallJob, job_id).status == InstallStatus.ACCEPTED
        assert db.get(Order, order_id).status == OrderStatus.INSTALLED
