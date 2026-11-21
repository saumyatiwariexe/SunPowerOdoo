"""Exercise real sessions in separate processes without touching the demo DB."""
import json
import os
from pathlib import Path
import subprocess
import sys


def test_public_enquiry_survives_process_restart(tmp_path):
    env = {
        **os.environ,
        "DATABASE_URL": "sqlite:///" + (tmp_path / "restart.sqlite").as_posix(),
        "JWT_SECRET": "persistence-test-only-secret-32-characters",
    }
    backend = Path(__file__).resolve().parents[1]

    def run(code):
        result = subprocess.run(
            [sys.executable, "-c", code], cwd=backend, env=env,
            text=True, capture_output=True, timeout=30, check=True,
        )
        return json.loads(result.stdout.strip().splitlines()[-1])

    saved = run('''
import json
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
import app.models_registry
from app.core.db import Base, get_engine
from app.main import create_app
from seed.seed_users import seed_users
Base.metadata.create_all(get_engine())
with Session(get_engine()) as db, db.begin():
    seed_users(db, password="restart-test-password")
with TestClient(create_app()) as client:
    response = client.post("/api/v1/public/enquiries", json={
        "name": "Restart persistence customer", "phone": "9876543210",
        "address": "Test roof", "pincode": "560001", "requested_kw": 3,
        "system_type": "ON_GRID", "subsidy_interest": True,
    })
    assert response.status_code == 201, response.text
    print(json.dumps(response.json()["data"]))
''')
    # No schema setup, seed, dependency overrides or cached session in process 2.
    restored = run('''
import json
from fastapi.testclient import TestClient
from app.main import create_app
with TestClient(create_app()) as client:
    response = client.post("/api/v1/auth/login", json={
        "email": "sales@sunpower.test", "password": "restart-test-password",
    })
    assert response.status_code == 200, response.text
    response = client.get("/api/v1/leads")
    assert response.status_code == 200, response.text
    print(json.dumps(response.json()))
''')
    assert restored["meta"]["total"] == 1
    row = restored["data"][0]
    assert row["id"] == saved["lead_id"]
    assert row["customer_id"] == saved["customer_id"]
    assert row["customer"]["name"] == "Restart persistence customer"
    assert row["status"] == "NEW"
