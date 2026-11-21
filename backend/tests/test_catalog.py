import bcrypt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

import app.models_registry  # noqa: F401
from app.core import db as db_module
from app.core.config import Settings, get_settings
from app.core.db import Base
from app.main import create_app
from app.modules.catalog.models import Package, Product, SystemType
from app.modules.catalog.service import get_package_bom
from app.modules.users.models import Role, User
from app.modules.inventory.models import SerialUnit, StockMovement
from seed.seed_catalog import seed_catalog
from seed.seed_inventory import seed_inventory

PRODUCTS = "/api/v1/products"
PACKAGES = "/api/v1/packages"
PASSWORD = "test-credential"


@pytest.fixture
def engine(monkeypatch):
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, _):
        connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    monkeypatch.setattr(db_module, "get_engine", lambda: engine)
    password_hash = bcrypt.hashpw(PASSWORD.encode(), bcrypt.gensalt(rounds=4)).decode()
    with Session(engine) as db:
        for role in (Role.DIRECTOR, Role.SALES, Role.WAREHOUSE, Role.CREW):
            db.add(User(name=role.title(), email=f"{role.lower()}@sunpower.test",
                        role=role, password_hash=password_hash))
        db.commit()
    yield engine
    engine.dispose()


@pytest.fixture
def client(engine):
    app = create_app()
    app.dependency_overrides[get_settings] = lambda: Settings(jwt_secret="x" * 32)
    with TestClient(app) as client:
        yield client


def sign_in(client, role="director"):
    response = client.post("/api/v1/auth/login", json={"email": f"{role}@sunpower.test", "password": PASSWORD})
    assert response.status_code == 200


def product_payload(sku="panel-500"):
    return {
        "sku": sku,
        "name": "Solar panel",
        "category": "PANEL",
        "unit": "unit",
        "tracks_serial": True,
        "warranty_months": 240,
        "cost_paise": 700_000,
        "price_paise": 900_000,
    }


def add_product(client, sku="panel-500"):
    response = client.post(PRODUCTS, json=product_payload(sku))
    assert response.status_code == 201, response.text
    return response.json()["data"]


def package_payload(product_id, installation_id):
    return {
        "name": "On-Grid 1 kW",
        "system_type": "ON_GRID",
        "capacity_kw": 1,
        "price_paise": 1_800_000,
        "items": [{"product_id": product_id, "qty": 2}, {"product_id": installation_id, "qty": 1}],
    }


def test_product_roles_money_search_and_unique_sku(client):
    assert client.get(PRODUCTS).status_code == 401
    sign_in(client, "crew")
    assert client.get(PRODUCTS).status_code == 403
    sign_in(client, "warehouse")
    assert client.get(PRODUCTS).status_code == 200
    assert client.post(PRODUCTS, json=product_payload()).status_code == 403

    sign_in(client)
    product = add_product(client)
    assert product["sku"] == "PANEL-500"
    assert product["on_hand"] == 0
    dup = client.post(PRODUCTS, json=product_payload("PANEL-500"))
    assert dup.status_code == 409
    assert dup.json()["error"]["code"] == "DUPLICATE_SKU"
    bad = client.patch(f"{PRODUCTS}/{product['id']}", json={"price_paise": 910_000.0})
    assert bad.status_code == 400
    bad_stock = client.patch(f"{PRODUCTS}/{product['id']}", json={"on_hand": 9})
    assert bad_stock.status_code == 400
    updated = client.patch(f"{PRODUCTS}/{product['id']}", json={"warranty_months": None, "price_paise": 910_000})
    assert updated.status_code == 200
    assert updated.json()["data"]["warranty_months"] is None
    data = client.get(PRODUCTS, params={"q": "panel-500", "page_size": 1}).json()
    assert data["meta"] == {"page": 1, "page_size": 1, "total": 1}
    assert data["data"][0]["price_paise"] == 910_000
    assert client.get(PRODUCTS, params={"q": "%"}).json()["data"] == []


def test_bom_replacement_and_invalid_patch_is_atomic(client, engine):
    sign_in(client)
    first = add_product(client)
    second = add_product(client, "PANEL-600")
    installation = client.post(PRODUCTS, json={**product_payload("INSTALLATION"), "category": "SERVICE"})
    assert installation.status_code == 201
    installation_id = installation.json()["data"]["id"]
    assert client.patch(f"{PRODUCTS}/{installation_id}", json={"sku": "RENAMED"}).status_code == 409
    payload = package_payload(first["id"], installation_id)
    response = client.post(PACKAGES, json=payload)
    assert response.status_code == 201, response.text
    package_id = response.json()["data"]["id"]
    route = f"{PACKAGES}/{package_id}"
    dup = client.post(PACKAGES, json=payload)
    assert dup.status_code == 409
    assert dup.json()["error"]["code"] == "DUPLICATE_PACKAGE"
    invalid = client.patch(route, json={"name": "Invalid", "items": [{"product_id": 999, "qty": 1}]})
    assert invalid.status_code == 409
    current = client.get(route).json()["data"]
    assert current["name"] == payload["name"]
    assert current["items"] == payload["items"]
    assert client.patch(route, json={"capacity_kw": None}).status_code == 409
    repeated_item = [{"product_id": first["id"], "qty": 1}] * 2
    assert client.patch(route, json={"items": repeated_item}).status_code == 400

    expanded = [
        {"product_id": first["id"], "qty": 3},
        {"product_id": second["id"], "qty": 1},
        payload["items"][1],
    ]
    missing_installation = client.patch(route, json={"items": expanded[:-1]})
    assert missing_installation.status_code == 409
    assert missing_installation.json()["error"]["code"] == "INSTALLATION_REQUIRED"
    response = client.patch(route, json={"items": expanded})
    assert response.status_code == 200, response.text
    assert response.json()["data"]["items"] == expanded
    remaining = expanded[1:]
    response = client.patch(route, json={"items": remaining, "active": False})
    assert response.status_code == 200, response.text
    assert client.get(PACKAGES, params={"status": "ACTIVE"}).json()["data"] == []
    sign_in(client, "sales")
    assert client.get(route).json()["data"]["items"] == remaining
    assert client.patch(route, json={"name": "Denied"}).status_code == 403
    with Session(engine) as db:
        items = get_package_bom(db, package_id)
        assert [(item.product.sku, item.qty) for item in items] == [("PANEL-600", 1), ("INSTALLATION", 1)]


def test_demo_seed_system_sizes_and_installation(engine):
    with Session(engine) as db:
        seed_catalog(db)
        seed_catalog(db)
        packages = list(db.scalars(select(Package)))
        assert len(packages) == 11
        assert len(list(db.scalars(select(Product)))) == 12
        assert {
            (package.system_type, package.capacity_kw)
            for package in packages if package.system_type is not None
        } == {(kind, kw) for kind in SystemType for kw in range(1, 6)}
        for package in packages:
            items = get_package_bom(db, package.id)
            parts = {item.product.sku: item.qty for item in items}
            if package.system_type is None:
                assert package.name == "Solar Panel Set"
                assert "INSTALLATION" not in parts
            else:
                assert parts["CONTROLLER"] == 1
                assert parts["INSTALLATION"] == 1
                assert parts["PANEL-500"] == 2 * package.capacity_kw
            assert package.price_paise == sum(item.product.price_paise * item.qty for item in items)
        db.rollback()
    with Session(engine) as db:
        assert db.scalar(select(Package.id).limit(1)) is None


def test_reseed_upgrades_existing_controller_stock_and_kit_once(engine):
    with Session(engine) as db:
        seed_catalog(db)
        controller = db.scalar(select(Product).where(Product.sku == "CONTROLLER"))
        kit = db.scalar(select(Package).where(Package.name == "On-Grid 3 kW"))
        list_price = kit.price_paise
        kit.items.remove(next(item for item in kit.items if item.product_id == controller.id))
        kit.price_paise -= controller.price_paise
        controller.tracks_serial = False
        controller.warranty_months = None
        seed_inventory(db)
        count = controller.on_hand
        for _ in range(2):
            seed_catalog(db)
            seed_inventory(db)
        assert (controller.tracks_serial, controller.warranty_months) == (True, 24)
        assert kit.price_paise == list_price
        assert sum(item.qty for item in kit.items if item.product_id == controller.id) == 1
        serials = list(db.scalars(select(SerialUnit.serial_no).where(SerialUnit.product_id == controller.id)))
        assert len(set(serials)) == count == controller.on_hand
        purchases = list(db.scalars(select(StockMovement).where(StockMovement.product_id == controller.id)))
        assert len(purchases) == 1


def test_public_catalog_includes_systems_and_hardware_package(client, engine):
    with Session(engine) as db:
        seed_catalog(db)
        db.commit()
    data = client.get("/api/v1/public/packages").json()["data"]
    assert len(data) == 11
    assert any(p["system_type"] is None and p["capacity_kw"] is None for p in data)
