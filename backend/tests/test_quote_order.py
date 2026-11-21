from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, func, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

import app.models_registry  # noqa: F401
from app.core import db as db_module
from app.core.config import Settings
from app.core.deps import get_current_user
from app.core.errors import AppError
from app.core.numbering import Counter, NumberPrefix, seed_counters
from app.main import create_app
from app.modules.catalog.models import Package
from app.modules.leads.models import Lead, LeadSource, LeadStatus, SystemType
from app.modules.orders import service as orders_service
from app.modules.orders.models import Order
from app.modules.quotes import service as quotes_service
from app.modules.quotes.models import Quote, QuoteStatus
from app.modules.users.models import Customer, Role, User

QUOTES = "/api/v1/quotes"
ORDERS = "/api/v1/orders"


@pytest.fixture
def database(monkeypatch):
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, _):
        connection.execute("PRAGMA foreign_keys=ON")

    db_module.Base.metadata.create_all(engine)
    monkeypatch.setattr(db_module, "get_engine", lambda: engine)
    monkeypatch.setattr(orders_service, "get_settings", lambda: Settings(advance_percent=30))

    with Session(engine) as db:
        customer = Customer(name="Customer", phone="9999999999", address="Test", pincode="560001")
        package = Package(name="Test package", price_paise=125)
        db.add_all([customer, package])
        db.flush()
        lead = Lead(
            customer_id=customer.id,
            source=LeadSource.CALL,
            requested_kw=1,
            system_type=SystemType.ON_GRID,
            status=LeadStatus.QUOTED,
        )
        db.add(lead)
        db.flush()
        quote = Quote(
            number="QT-TEST",
            lead_id=lead.id,
            customer_id=customer.id,
            package_id=package.id,
            subtotal_paise=125,
            subsidy_paise=24,
            total_paise=101,
            valid_until=datetime.now(UTC).date() + timedelta(days=2),
        )
        db.add(quote)
        seed_counters(db)
        quote_id = quote.id
        db.commit()

    yield engine, quote_id
    engine.dispose()


@pytest.fixture
def client(database):
    app = create_app()
    app.dependency_overrides[get_current_user] = lambda: User(role=Role.SALES)
    with TestClient(app) as client:
        yield client


def test_send_accept_and_repeat_returns_one_draft_order(client, database):
    engine, quote_id = database
    quote_url = f"{QUOTES}/{quote_id}"
    assert client.post(f"{quote_url}/accept").json()["error"]["code"] == "QUOTE_NOT_SENT"
    assert client.post(f"{quote_url}/send").json()["data"]["status"] == "SENT"

    response = client.post(f"{quote_url}/accept")
    assert response.status_code == 200
    order = response.json()["data"]
    assert order["quote_id"] == quote_id
    assert order["status"] == "DRAFT"
    assert order["number"] == "ORD-0001"
    assert order["total_paise"] == 101
    assert order["advance_min_paise"] == 31
    assert order["confirmed_at"] is None
    assert client.get(quote_url).json()["data"]["status"] == "ACCEPTED"
    assert client.get(f"{ORDERS}/{order['id']}").json()["data"] == {**order, "paid_paise": 0}
    listing = client.get(ORDERS).json()
    assert listing["data"] == [order]
    assert listing["meta"]["total"] == 1
    assert client.post(f"{quote_url}/accept").json()["data"] == order
    with Session(engine) as db:
        assert quotes_service.convert_to_order(db, quote_id).id == order["id"]
        assert db.scalar(select(func.count()).select_from(Order)) == 1
        counter = db.scalar(select(Counter).where(Counter.name == NumberPrefix.ORDER))
        assert counter.value == 1


def test_convert_requires_accepted_quote(database):
    engine, quote_id = database
    with Session(engine) as db, pytest.raises(AppError) as exc:
        quotes_service.convert_to_order(db, quote_id)
    assert exc.value.code == "QUOTE_NOT_ACCEPTED"


def test_expired_sent_quote_cannot_be_accepted(client, database):
    engine, quote_id = database
    with Session(engine) as db:
        quote = db.get(Quote, quote_id)
        quote.status = QuoteStatus.SENT
        quote.valid_until = datetime.now(UTC).date() - timedelta(days=1)
        db.commit()
    response = client.post(f"{QUOTES}/{quote_id}/accept")
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "QUOTE_EXPIRED"
    with Session(engine) as db:
        assert db.get(Quote, quote_id).status == QuoteStatus.SENT
        assert db.scalar(select(Order.id)) is None


def test_accept_rolls_back_when_order_creation_fails(client, database, monkeypatch):
    engine, quote_id = database

    def fail_numbering(*args):
        raise AppError("COUNTER_NOT_INITIALIZED", "Run the database seed.", 503)

    assert client.post(f"{QUOTES}/{quote_id}/send").status_code == 200
    monkeypatch.setattr(orders_service, "next_number", fail_numbering)
    assert client.post(f"{QUOTES}/{quote_id}/accept").status_code == 503
    with Session(engine) as db:
        assert db.get(Quote, quote_id).status == QuoteStatus.SENT
        assert db.scalar(select(Order.id)) is None
