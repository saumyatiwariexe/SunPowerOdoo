import csv
import io
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest
from dateutil.relativedelta import relativedelta
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

import app.models_registry  # noqa: F401
from app.core import db as db_module
from app.core.config import Settings, get_settings
from app.core.deps import get_current_user
from app.core.errors import AppError
from app.core.numbering import seed_counters
from app.main import create_app
from app.modules.billing.models import Invoice, Payment
from app.modules.catalog.models import Package
from app.modules.deliveries.models import Delivery, DeliveryScan
from app.modules.installs import service as installs
from app.modules.installs.models import InstallCrew, InstallJob, InstallStatus
from app.modules.leads.models import Lead, LeadSource, LeadStatus, SystemType
from app.modules.orders import service as orders
from app.modules.orders.models import Order, OrderStatus
from app.modules.quotes.models import Quote, QuoteStatus
from app.modules.quotes.service import convert_to_order
from app.modules.users.models import Customer, Role, User
from app.modules.warranty.models import Warranty
from app.modules.subsidy.models import SubsidyClaim
from seed.seed_subsidy import backfill_subsidy_claims
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
    monkeypatch.setattr(db_module, "get_engine", lambda: engine)
    settings = Settings(advance_percent=30, uploads_dir=tmp_path)
    monkeypatch.setattr(orders, "get_settings", lambda: settings)

    with Session(engine) as db:
        actors = {}
        for key, role in (
            ("director", Role.DIRECTOR), ("surveyor", Role.SURVEYOR),
            ("other_surveyor", Role.SURVEYOR), ("crew", Role.CREW), ("other_crew", Role.CREW),
            ("warehouse", Role.WAREHOUSE), ("support", Role.SUPPORT),
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
            engine=engine, client=client,
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


def add_order(stage, quote_number, subsidy=0):
    with Session(stage.engine) as db:
        lead = db.get(Lead, stage.lead_id)
        quote = Quote(
            number=quote_number, lead_id=lead.id, customer_id=lead.customer_id, package_id=stage.package_id,
            subtotal_paise=101 + subsidy, subsidy_paise=subsidy, total_paise=101, status=QuoteStatus.ACCEPTED,
            valid_until=datetime.now(UTC).date() + timedelta(days=1),
        )
        db.add(quote)
        db.flush()
        order_id = convert_to_order(db, quote.id).id
        db.commit()
        return order_id


def record_advance(stage, order_id, paise):
    response = stage.client.post(f"{API}/orders/{order_id}/payments", json={"amount_paise": paise, "method": "UPI"})
    assert response.status_code == 200, response.text


def test_report_counts_cash_once_on_receipt_date(workspace):
    stage = workspace
    order_id = add_order(stage, "QT-CASH")
    record_advance(stage, order_id, 31)
    url = f"{API}/reports/summary?range=today"
    assert stage.client.get(url).json()["data"]["collected_paise"] == 31
    invoice = stage.client.post(f"{API}/invoices", json={"order_id": order_id}).json()["data"]
    data = stage.client.get(url).json()["data"]
    assert (data["collected_paise"], data["outstanding_paise"]) == (31, 70)
    with Session(stage.engine) as db:
        db.get(Invoice, invoice["id"]).issued_at -= timedelta(days=45)
        db.scalar(select(Payment).where(Payment.order_id == order_id)).paid_at -= timedelta(days=45)
        db.commit()
    record_advance(stage, order_id, 70)
    data = stage.client.get(url).json()["data"]
    assert (data["revenue_paise"], data["collected_paise"], data["outstanding_paise"]) == (0, 70, 0)


def test_profit_period_and_csv_return_the_same_jobs(workspace):
    stage = workspace
    job, current_id = confirmed_job(stage, "QT-CURRENT")
    _, old_id = confirmed_job(stage, "QT-OLD")
    with Session(stage.engine) as db:
        db.get(Order, old_id).confirmed_at -= timedelta(days=45)
        db.commit()
    reports = f"{API}/reports"
    for period in ("today", "week", "month"):
        params = {"range": period, "sort": "asc"}
        rows = stage.client.get(reports + "/profit-per-job", params=params).json()["data"]
        assert [r["order_id"] for r in rows] == [current_id]
        exported = stage.client.get(reports + "/export.csv", params=params)
        assert list(csv.DictReader(io.StringIO(exported.text))) == [
            {key: str(value) for key, value in row.items()} for row in rows
        ]
    with Session(stage.engine) as db:
        shift = db.get(InstallJob, job)
        shift.started_at = datetime(2025, 3, 1, 9, tzinfo=UTC)
        shift.finished_at = shift.started_at + timedelta(minutes=30)
        tech = db.get(User, stage.actors["crew"].id)
        tech.hourly_rate_paise = 20000
        db.add(InstallCrew(install_job_id=job, user_id=tech.id))
        db.commit()
    hours = stage.client.get(reports + "/technician-hours?month=2025-03").json()["data"]
    assert [(r["hours_worked"], r["amount_due_paise"]) for r in hours] == [(0.5, 10000)]
    for month, expected in [("2025-03", hours), ("2025-04", [])]:
        response = stage.client.get(reports + "/export.csv", params={"report": "hours", "month": month})
        reader = csv.DictReader(io.StringIO(response.text))
        assert "hours_worked" in reader.fieldnames
        assert list(reader) == [{k: str(v) for k, v in row.items()} for row in expected]


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
        assert db.scalar(select(Delivery.id)) is None

    record_advance(stage, order_id, 1)
    confirmed = stage.client.post(url)
    assert confirmed.status_code == 200, confirmed.text
    assert confirmed.json()["data"]["status"] == "CONFIRMED"
    assert confirmed.json()["data"]["confirmed_at"]
    assert stage.client.post(url).json()["data"] == confirmed.json()["data"]
    with Session(stage.engine) as db:
        assert db.scalar(select(func.count()).select_from(InstallJob)) == 1
        assert db.scalar(select(func.count()).select_from(Delivery)) == 1


def test_subsidy_claim_is_created_once_only_for_interested_confirmed_orders(workspace):
    stage = workspace
    _, uninterested = confirmed_job(stage, "QT-NO-CLAIM")
    assert stage.client.get(f"{API}/subsidy").json()["data"] == []
    pending = add_order(stage, "QT-CLAIM", subsidy=15)
    with Session(stage.engine) as db:
        db.get(Lead, stage.lead_id).subsidy_interest = True
        db.commit()
    confirm = f"{API}/orders/{pending}/confirm"
    assert stage.client.post(confirm).status_code == 409
    assert stage.client.get(f"{API}/subsidy").json()["data"] == []
    record_advance(stage, pending, 31)
    assert stage.client.post(confirm).status_code == 200
    assert stage.client.post(confirm).status_code == 200
    claims = stage.client.get(f"{API}/subsidy").json()["data"]
    assert [(c["order_id"], c["amount_paise"], c["status"]) for c in claims] == [(pending, 15, "NOT_APPLIED")]
    claim_url = f"{API}/subsidy/{claims[0]['id']}"
    assert stage.client.patch(claim_url, json={"status": "SUBMITTED", "scheme": "Roof grant"}).status_code == 200
    with Session(stage.engine) as db:
        # The first order now represents a previously confirmed, newly eligible order.
        backfill_subsidy_claims(db)
        backfill_subsidy_claims(db)
        assert set(db.scalars(select(SubsidyClaim.order_id))) == {uninterested, pending}
        db.commit()
    assert stage.client.get(claim_url).json()["data"]["scheme"] == "Roof grant"


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
        assert db.scalar(select(Delivery.id)) is None


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
    now = datetime.now(UTC) - timedelta(hours=1)
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
    stage.state.actor = stage.actors["director"]
    summary = f"{API}/reports/summary"
    # Both states must count in the period that contains the recorded finish.
    assert stage.client.get(summary).json()["data"]["jobs_completed"] == 1
    stage.state.actor = stage.actors["crew"]
    assert stage.client.post(f"{root}/accept").json()["data"]["status"] == "ACCEPTED"
    stage.state.actor = stage.actors["director"]
    assert stage.client.get(summary).json()["data"]["jobs_completed"] == 1
    with Session(stage.engine) as db:
        assert db.get(InstallJob, job_id).status == InstallStatus.ACCEPTED
        assert db.get(Order, order_id).status == OrderStatus.INSTALLED


def test_core_chain_lead_to_warranty_and_ticket_billing(workspace):
    stage = workspace
    client = stage.client
    now = datetime.now(UTC)
    request = client.post(
        f"{API}/leads/{stage.lead_id}/survey",
        json={"surveyor_id": stage.actors["surveyor"].id, "scheduled_at": now.isoformat()},
    )
    assert request.status_code == 201, request.text
    survey_id = request.json()["data"]["id"]
    stage.state.actor = stage.actors["surveyor"]
    assert client.post(
        f"{API}/surveys/{survey_id}/submit",
        json={"roof_direction": "South", "tilt_degrees": 24, "cable_distance_m": 12},
    ).status_code == 200
    stage.state.actor = stage.actors["director"]
    assert client.post(f"{API}/surveys/{survey_id}/approve", json={"note": "Approved"}).status_code == 200
    draft = client.post(
        f"{API}/quotes",
        json={"lead_id": stage.lead_id, "package_id": stage.package_id,
              "valid_until": (now.date() + timedelta(days=10)).isoformat()},
    )
    assert draft.status_code == 201, draft.text
    path = f"{API}/quotes/{draft.json()['data']['id']}"
    assert client.post(f"{path}/send").status_code == 200
    order = client.post(f"{path}/accept").json()["data"]
    record_advance(stage, order["id"], order["advance_min_paise"])
    assert client.post(f"{API}/orders/{order['id']}/confirm").status_code == 200
    competing_order = add_order(stage, "QT-COMPETING")
    record_advance(stage, competing_order, 31)
    assert client.post(f"{API}/orders/{competing_order}/confirm").status_code == 200

    stage.state.actor = stage.actors["warehouse"]
    deliveries = {row["order_id"]: row for row in client.get(f"{API}/deliveries").json()["data"]}
    primary_delivery = deliveries[order["id"]]["id"]
    competing_delivery = deliveries[competing_order]["id"]
    path = f"{API}/deliveries/{primary_delivery}"
    assert client.post(f"{path}/dispatch").json()["error"]["code"] == "INCOMPLETE_SERIAL_SCANS"
    lines = client.get(path).json()["data"]["lines"]
    assert all(line["sku"] != "INSTALLATION" for line in lines)
    serials = []
    for line in lines:
        numbers = [f"CHAIN-{line['sku']}-{i}" for i in range(line["qty_required"])] if line["tracks_serial"] else []
        stock = client.post(
            f"{API}/stock/receive",
            json={"product_id": line["product_id"], "qty": line["qty_required"],
                  "purchase_cost_paise": 100, "serial_numbers": numbers},
        )
        assert stock.status_code == 200, stock.text
        serials.extend((line["sku"], number) for number in numbers)
        for number in numbers:
            if line["sku"] == "CONTROLLER":
                continue
            scanned = client.post(f"{path}/scan", json={"serial_no": number})
            assert scanned.status_code == 200, scanned.text

    controller = next(number for sku, number in serials if sku == "CONTROLLER")
    missing = client.post(f"{path}/dispatch")
    assert missing.status_code == 409
    assert "Charge controller" in missing.json()["error"]["message"]
    assert client.post(f"{path}/scan", json={"serial_no": controller}).status_code == 200
    already_scanned = serials[0][1]
    assert client.post(f"{path}/scan", json={"serial_no": already_scanned}).status_code == 409
    assert client.post(
        f"{API}/deliveries/{competing_delivery}/scan", json={"serial_no": already_scanned}
    ).status_code == 409
    with Session(stage.engine) as db:
        existing_scan = db.scalar(select(DeliveryScan).where(DeliveryScan.delivery_id == primary_delivery))
        db.add(DeliveryScan(delivery_id=competing_delivery, serial_unit_id=existing_scan.serial_unit_id,
                            scanned_by_id=stage.actors["warehouse"].id, scanned_at=now))
        with pytest.raises(IntegrityError):
            db.flush()

    assert client.post(f"{path}/dispatch").status_code == 200
    delivered = client.post(f"{path}/deliver")
    assert delivered.status_code == 200, delivered.text
    assert delivered.json()["data"]["status"] == "DELIVERED"
    stage.state.actor = stage.actors["director"]
    profit = client.get(f"{API}/reports/profit-per-job").json()["data"]
    job = next(row for row in profit if row["order_id"] == order["id"])
    # Each physical unit, both scanned and bulk, was received at 100 paise.
    expected_parts = sum(line["qty_required"] * 100 for line in lines)
    assert job["parts_paise"] == expected_parts
    assert job["profit_paise"] == -expected_parts
    stage.state.actor = stage.actors["support"]
    warranty_ids = []
    for sku, number in serials:
        warranty = client.get(f"{API}/lookup", params={"serial": number}).json()["data"]
        months = 240 if sku == "PANEL-500" else 24
        start = datetime.fromisoformat(warranty["start_date"]).date()
        assert warranty["end_date"] == (start + relativedelta(months=months)).isoformat()
        assert warranty["in_warranty"]
        warranty_ids.append(warranty["warranty_id"])
    assert len(set(warranty_ids)) == len(serials)
    assert len(client.get(f"{API}/lookup", params={"phone": "9999999999"}).json()["data"]) == len(serials)

    panel = next(number for sku, number in serials if sku == "PANEL-500")
    inverter = next(number for sku, number in serials if sku.startswith("INV-"))
    inverter_coverage = client.get(f"{API}/lookup", params={"serial": inverter}).json()["data"]
    with Session(stage.engine) as db:
        past = db.get(Warranty, inverter_coverage["warranty_id"])
        past.start_date = now.date() - relativedelta(months=26)
        past.end_date = past.start_date + relativedelta(months=24)
        db.commit()
    assert not client.get(f"{API}/lookup", params={"serial": inverter}).json()["data"]["in_warranty"]

    for serial, expected_billable in ((panel, False), (inverter, True)):
        response = client.post(
            f"{API}/tickets", json={"serial_no": serial, "fault_code": "OUTPUT", "description": "Low output"}
        )
        assert response.status_code == 201, response.text
        ticket = response.json()["data"]
        assert ticket["billable"] is expected_billable
        ticket_path = f"{API}/tickets/{ticket['id']}"
        assert client.patch(ticket_path, json={"status": "IN_PROGRESS"}).status_code == 200
        assert client.post(f"{ticket_path}/resolve", json={"resolution": "Output restored"}).status_code == 200
        stage.state.actor = stage.actors["director"]
        assert client.get(f"{API}/reports/summary").json()["data"]["open_tickets"] == 1
        stage.state.actor = stage.actors["support"]
        blocked = client.post(f"{ticket_path}/close")
        assert blocked.status_code == 409
        assert blocked.json()["error"]["code"] == "CUSTOMER_CONFIRMATION_REQUIRED"
        assert client.post(f"{ticket_path}/confirm").status_code == 200
        if expected_billable:
            unpriced = client.post(f"{ticket_path}/close")
            assert unpriced.status_code == 409
            assert unpriced.json()["error"]["code"] == "BILLABLE_LINES_REQUIRED"
        for kind, qty, unit_price in (("PART", 2, 500), ("LABOUR", 1, 600)):
            line = {"type": kind, "description": kind, "qty": qty, "unit_price_paise": unit_price}
            assert client.post(f"{ticket_path}/lines", json=line).status_code == 201
        assert client.post(f"{ticket_path}/close").json()["error"]["code"] == "CUSTOMER_CONFIRMATION_REQUIRED"
        assert client.post(f"{ticket_path}/confirm").status_code == 200
        closed = client.post(f"{ticket_path}/close")
        assert closed.status_code == 200, closed.text
        stage.state.actor = stage.actors["director"]
        assert client.get(f"{API}/reports/summary").json()["data"]["open_tickets"] == 0
        stage.state.actor = stage.actors["support"]
        closure = closed.json()["data"]
        assert closure["ticket"]["status"] == "CLOSED"
        assert (closure["invoice_id"] is not None) is expected_billable
        assert client.post(f"{ticket_path}/close").json()["data"] == closure
        if expected_billable:
            invoice = client.get(f"{API}/invoices/{closure['invoice_id']}").json()["data"]
            assert invoice["total_paise"] == 1_600
            assert len(invoice["lines"]) == 2
    with Session(stage.engine) as db:
        assert db.scalar(select(func.count()).select_from(Invoice)) == 1


def test_lead_inbox_and_call_history_follow_role(workspace):
    client = workspace.client
    path = f"{API}/leads/{workspace.lead_id}"
    response = client.post(
        path + "/calls", json={"outcome": "Visit requested", "called_at": datetime.now(UTC).isoformat()}
    )
    assert response.status_code == 201
    assert client.get(path).json()["data"]["calls"][0]["outcome"] == "Visit requested"
    row = client.get(f"{API}/leads").json()["data"][0]
    assert row["customer"]["name"] == "Customer"
    assert "calls" not in row
    workspace.state.actor = workspace.actors["support"]
    assert "customer" not in client.get(path).json()["data"]
    assert "calls" not in client.get(path).json()["data"]


def test_sales_can_enter_a_phone_enquiry_for_a_new_customer(workspace):
    client = workspace.client
    response = client.post(f"{API}/leads", json={
        "name": "Phone enquiry", "phone": "9876543210", "address": "24 Solar Lane",
        "pincode": "144411", "source": "CALL", "requested_kw": 3, "system_type": "ON_GRID",
    })
    assert response.status_code == 201
    detail = client.get(f"{API}/leads/{response.json()['data']['id']}").json()["data"]
    assert detail["customer"]["phone"] == "9876543210"
    assert detail["source"] == "CALL"

def test_scheduling_options_follow_contact_and_exclude_booked_visits(workspace):
    stage = workspace
    opts = f"{API}/surveys/scheduling-options"
    lead_path = f"{API}/leads/{stage.lead_id}"
    visit = {"surveyor_id": stage.actors["surveyor"].id, "scheduled_at": datetime.now(UTC).isoformat()}
    with Session(stage.engine) as db:
        db.get(Lead, stage.lead_id).status = LeadStatus.NEW
        db.get(User, stage.actors["other_surveyor"].id).active = False
        db.commit()
    data = stage.client.get(opts).json()["data"]
    assert data["leads"] == []
    assert data["surveyors"] == [{"id": visit["surveyor_id"], "name": "surveyor"}]
    denied = stage.client.post(lead_path + "/survey", json=visit)
    assert denied.status_code == 409 and "customer call" in denied.json()["error"]["message"]
    assert stage.client.post(lead_path + "/calls", json={"outcome": "Ready", "called_at": visit["scheduled_at"]}).is_success
    assert stage.client.get(opts).json()["data"]["leads"] == [{"id": stage.lead_id, "name": "Customer"}]
    assert stage.client.post(lead_path + "/survey-request").is_success
    booked = stage.client.post(lead_path + "/survey", json=visit).json()["data"]
    data = stage.client.get(opts, params={"lead_id": stage.lead_id}).json()["data"]
    assert data["leads"] == [] and data["existing_survey_id"] == booked["id"]
    stage.state.actor = stage.actors["surveyor"]
    assert stage.client.get(opts).status_code == 403
