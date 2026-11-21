from datetime import timedelta
from io import BytesIO
from typing import Annotated

import bcrypt
import pytest
from fastapi import Depends, UploadFile
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

import app.models_registry  # noqa: F401
from app.core import db as db_module
from app.core.config import Settings, get_settings
from app.core.db import Base, get_db
from app.core.deps import require_roles
from app.core.errors import AppError
from app.core.money import minimum_advance_paise
from app.core.numbering import NumberPrefix, next_number, seed_counters
from app.core.uploads import MAX_IMAGE_BYTES, save_image
from app.main import create_app
from app.modules.users.models import Role, User
from app.modules.users.service import LOGIN_ATTEMPTS_PER_WINDOW

LOGIN = "/api/v1/auth/login"
ME = "/api/v1/auth/me"
LOGOUT = "/api/v1/auth/logout"
PASSWORD = "test-credential"


@pytest.fixture
def engine(monkeypatch):
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    monkeypatch.setattr(db_module, "get_engine", lambda: engine)
    with Session(engine) as db:
        db.add(
            User(
                name="Test Sales",
                email="sales@sunpower.test",
                role=Role.SALES,
                password_hash=bcrypt.hashpw(PASSWORD.encode(), bcrypt.gensalt(rounds=4)).decode(),
            )
        )
        seed_counters(db)
        db.commit()
    yield engine
    engine.dispose()


@pytest.fixture
def client(engine):
    app = create_app()
    app.dependency_overrides[get_settings] = lambda: Settings(jwt_secret="x" * 32)

    @app.get("/api/v1/director", dependencies=[Depends(require_roles("DIRECTOR"))])
    def director():
        return {"data": True}

    @app.post("/allocate-and-fail")
    def allocate_and_fail(db: Annotated[Session, Depends(get_db)]):
        next_number(db, NumberPrefix.ORDER)
        raise AppError("RULE_VIOLATION", "Reject this write.", 409)

    with TestClient(app) as client:
        yield client


def login(client, password=PASSWORD):
    return client.post(LOGIN, json={"email": " SALES@sunpower.test ", "password": password})


def test_login_current_user_role_and_logout(client):
    assert client.get(ME).status_code == 401
    response = login(client)
    assert response.status_code == 200
    assert "httponly" in response.headers["set-cookie"].lower()
    assert "password_hash" not in response.json()["data"]
    assert client.get(ME).json()["data"]["role"] == "SALES"
    denied = client.get("/api/v1/director")
    assert denied.status_code == 403
    assert denied.json()["error"]["code"] == "FORBIDDEN"
    assert client.post(LOGOUT).status_code == 200
    assert client.get(ME).status_code == 401


def test_login_validation_does_not_echo_credentials(client):
    response = client.post(LOGIN, json={"email": "sales@sunpower.test", "password": PASSWORD, "x": 1})
    assert response.status_code == 422
    assert response.json()["error"]["details"][0]["loc"] == ["body", "x"]
    assert PASSWORD not in response.text


def test_login_attempts_are_rate_limited(client):
    for _ in range(LOGIN_ATTEMPTS_PER_WINDOW):
        assert login(client, "wrong-password").status_code == 401
    response = login(client)
    assert response.status_code == 429
    assert response.json()["error"]["code"] == "LOGIN_RATE_LIMIT"


def test_deactivated_user_cannot_reuse_cookie(client, engine):
    assert login(client).status_code == 200
    with Session(engine) as db:
        user = db.scalar(select(User))
        assert user.created_at.utcoffset() == timedelta(0)
        user.active = False
        db.commit()
    assert client.get(ME).status_code == 401


def test_failed_write_rolls_back_number(client, engine):
    assert client.post("/allocate-and-fail").status_code == 409
    with Session(engine) as db:
        assert next_number(db, NumberPrefix.ORDER) == "ORD-0001"
        assert next_number(db, NumberPrefix.ORDER) == "ORD-0002"
        db.commit()


def test_advance_rounds_up_and_rejects_float():
    assert minimum_advance_paise(101, 30) == 31
    with pytest.raises(ValueError):
        minimum_advance_paise(101.0, 30)


def test_upload_limits_type_and_uses_random_names(tmp_path):
    app = create_app()

    @app.post("/upload")
    async def upload(file: UploadFile):
        return {"name": await save_image(file, tmp_path)}

    with TestClient(app) as client:
        invalid = client.post("/upload", files={"file": ("spoof.png", b"plain text", "image/png")})
        assert invalid.status_code == 400
        large = client.post("/upload", files={"file": ("large.png", BytesIO(b"x" * (MAX_IMAGE_BYTES + 1)))})
        assert large.status_code == 413
        png = b"\x89PNG\r\n\x1a\n"
        response = client.post("/upload", files={"file": ("original.png", png, "image/png")})
        assert response.status_code == 200
        name = response.json()["name"]
        assert name != "original.png"
        assert (tmp_path / name).read_bytes() == png


def test_public_health_and_cors(client):
    health = client.get("/api/v1/public/health")
    assert health.json() == {"data": {"status": "ok"}}
    headers = {"Origin": get_settings().frontend_origin, "Access-Control-Request-Method": "POST"}
    accepted = client.options(LOGIN, headers=headers)
    assert accepted.headers["access-control-allow-credentials"] == "true"
    headers["Origin"] = "https://untrusted.example"
    assert "access-control-allow-origin" not in client.options(LOGIN, headers=headers).headers


def test_director_staff_directory_and_access_changes(client, engine):
    base = "/api/v1/users"
    with Session(engine) as db:
        sales = db.scalar(select(User).where(User.role == Role.SALES))
        sales_id = sales.id
        director = User(name="Director", email="director@sunpower.test", role=Role.DIRECTOR,
                        password_hash=sales.password_hash)
        db.add(director)
        db.commit()
        director_id = director.id

    assert client.get(base).status_code == 401
    login(client)
    assert client.get(base).status_code == 403
    assert client.patch(f"{base}/{sales_id}", json={"role": "DIRECTOR"}).status_code == 403
    assert client.post(LOGIN, json={"email": "director@sunpower.test", "password": PASSWORD}).status_code == 200
    payload = {"name": "Field worker", "email": " CREW2@example.com ", "password": " secret with spaces ",
               "role": "CREW", "phone": "555-0100", "hourly_rate_paise": 10425}
    created = client.post(base, json=payload)
    assert created.status_code == 201, created.text
    row = created.json()["data"]
    assert row["email"] == "crew2@example.com"
    assert "password" not in row and "password_hash" not in row
    detail = f"{base}/{row['id']}"
    assert client.get(detail).json()["data"] == row
    assert client.get(base, params={"page_size": 1, "page": 2}).json()["meta"]["total"] == 3
    assert client.post(base, json=payload).json()["error"]["code"] == "EMAIL_IN_USE"
    assert client.patch(detail, json={"hourly_rate_paise": 1.25}).status_code == 400
    assert client.patch(detail, json={"email": "sales@sunpower.test", "role": "SUPPORT"}).status_code == 409
    assert client.get(detail).json()["data"]["role"] == "CREW"
    assert client.patch(f"{base}/{director_id}", json={"active": False}).json()["error"]["code"] == "LAST_DIRECTOR"
    cookie = client.cookies.get("sunpower_session")
    assert client.post(LOGIN, json={"email": row["email"], "password": payload["password"]}).status_code == 200
    worker_cookie = client.cookies.get("sunpower_session")

    def switch(token):
        client.cookies.clear()
        client.cookies.set("sunpower_session", token, path="/api/v1")

    switch(cookie)
    updated = client.patch(detail, json={"role": "SUPPORT", "phone": None, "hourly_rate_paise": 20001})
    assert updated.json()["data"]["hourly_rate_paise"] == 20001
    switch(worker_cookie)
    assert client.get(ME).json()["data"]["role"] == "SUPPORT"
    switch(cookie)
    assert client.patch(detail, json={"active": False}).status_code == 200
    switch(worker_cookie)
    assert client.get(ME).status_code == 401

def test_database_url_overrides_postgres_defaults(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///release-check.sqlite")
    assert str(Settings(_env_file=None).database_url) == "sqlite:///release-check.sqlite"
