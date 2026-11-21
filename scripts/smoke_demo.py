"""Exercise the nine demo scenes against a running API backed by a throwaway DB.

Set QA_SEED_PASSWORD to the password used by the seed. Run from any directory:
    python scripts/smoke_demo.py --base-url http://127.0.0.1:8100/api/v1

Each run creates leads, payments, stock, jobs and tickets. Schema/model checks
use the checkout containing this script. EXIT 1 means failed or blocked checks.
"""
import argparse
import base64
import csv
import importlib
import io
import os
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack
from datetime import UTC, datetime, timedelta
from pathlib import Path
from threading import Barrier
from uuid import uuid4

try:
    import httpx
except ImportError:
    import httpx2 as httpx  # Client already pinned by this repo for FastAPI tests.
from dateutil.relativedelta import relativedelta

PNG = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jWZkAAAAASUVORK5CYII=")
ROLES = ("sales", "surveyor", "warehouse", "crew", "support", "director")


def assert_money(value):
    if isinstance(value, list):
        for item in value:
            assert_money(item)
    elif isinstance(value, dict):
        for key, item in value.items():
            if key.endswith("_paise") and item is not None:
                assert type(item) is int, f"R14 {key} must be integer paise"
            assert_money(item)


def error_body(response):
    body = response.json()["error"]
    assert isinstance(body.get("code"), str) and body["code"]
    assert isinstance(body.get("message"), str) and body["message"]
    assert isinstance(body.get("details"), list)
    return body


class Demo:
    def __init__(self, base, stack):
        self.clients = {role: stack.enter_context(httpx.Client(base_url=base, timeout=15))
                        for role in ("public", *ROLES)}
        self.ids = {}
        self.failures = []
        self.tag = uuid4().hex[:12]
        self.now = datetime.now(UTC)

    def run(self, label, fn):
        try:
            fn()
            print("PASS", label)
        except (AssertionError, KeyError, ValueError, StopIteration, httpx.HTTPError) as exc:
            self.failures.append(label)
            print("FAIL", label, "-", str(exc) or type(exc).__name__)

    def request(self, role, method, path, **kwargs):
        return self.clients[role].request(method, path, **kwargs)

    def data(self, role, method, path, **kwargs):
        res = self.request(role, method, path, **kwargs)
        assert res.is_success, f"{method} {path}: HTTP {res.status_code}: {res.text[:180]}"
        body = res.json()["data"]
        assert_money(body)
        return body

    def negative(self, label, role, method, path, expected, **kwargs):
        def check():
            res = self.request(role, method, path, **kwargs)
            why = error_body(res)
            assert res.status_code in expected, f"HTTP {res.status_code} ({why['code']}); expected {expected}"
        self.run(label, check)

    def login(self, role, password):
        row = self.data(role, "POST", "auth/login", json={"email": role + "@sunpower.test", "password": password})
        assert row["role"] == role.upper()
        self.ids[role] = row["id"]

    def rows(self, role, path):
        result = []
        page = 1
        while True:
            res = self.request(role, "GET", path, params={"page": page, "page_size": 100})
            assert res.is_success, f"GET {path}: HTTP {res.status_code}"
            body = res.json()
            assert_money(body)
            result.extend(body["data"])
            meta = body.get("meta", {})
            if len(result) >= meta.get("total", len(result)) or not meta.get("page_size"):
                return result
            assert body["data"], f"Empty intermediate page of {path}"
            page += 1

    def enquiry(self):
        return {"name": "QA " + self.tag, "phone": "9" + str(uuid4().int)[:9],
                "address": "QA roof", "pincode": "560001", "requested_kw": 3,
                "system_type": "ON_GRID", "subsidy_interest": True}

    def order(self, check_rules):
        visitor = self.enquiry()
        lead_id = self.data("public", "POST", "public/enquiries", json=visitor)["lead_id"]
        lead = f"leads/{lead_id}"
        assert any(r["id"] == lead_id for r in self.rows("sales", "leads")), "Enquiry missing from sales inbox"
        if check_rules:
            print("PASS Scene 1 public enquiry in sales inbox")
            self.negative("R1 no delete", "sales", "DELETE", lead, {405})
            self.negative("R1 loss requires reason", "sales", "POST", lead + "/lost", {400, 409, 422},
                          json={"lost_reason": ""})
            assert self.data("sales", "GET", lead)["status"] == "NEW"
        package = next(p for p in self.rows("sales", "packages")
                       if p["system_type"] == "ON_GRID" and p["capacity_kw"] == 3)
        template = self.data("sales", "GET", f"packages/{package['id']}")
        quote_input = {"lead_id": lead_id, "package_id": package["id"],
                       "valid_until": (self.now.date() + timedelta(days=10)).isoformat()}
        if check_rules:
            self.negative("R2 unapproved survey", "sales", "POST", "quotes", {409}, json=quote_input)
        self.data("sales", "POST", lead + "/calls", json={"outcome": "Proceed to survey", "grid_suitable": True,
                  "shadow_free_area_sqm": 32, "monthly_bill_paise": 350000, "called_at": self.now.isoformat()})
        self.data("sales", "POST", lead + "/survey-request")
        visit = self.data("sales", "POST", lead + "/survey", json={"surveyor_id": self.ids["surveyor"],
                          "scheduled_at": self.now.isoformat()})
        root = f"surveys/{visit['id']}"
        assert any(r["id"] == visit["id"] for r in self.rows("surveyor", "surveys/mine"))
        self.data("surveyor", "POST", root + "/submit", json={"roof_direction": "South", "tilt_degrees": 20,
                  "cable_distance_m": 12})
        self.data("sales", "POST", root + "/approve", json={"note": "Suitable roof"})
        if check_rules:
            print("PASS Scene 2 survey reviewed")
        quote = self.data("sales", "POST", "quotes", json=quote_input)
        assert Counter((r["product_id"], r["qty"]) for r in quote["lines"]) == Counter(
            (r["product_id"], r["qty"]) for r in template["items"]), "R3 BOM mismatch"
        root = f"quotes/{quote['id']}"
        self.data("sales", "POST", root + "/send")
        order = self.data("sales", "POST", root + "/accept")
        root = f"orders/{order['id']}"
        minimum = order["advance_min_paise"]
        if check_rules:
            print("PASS Scene 3 package quote accepted")
            self.negative("R14 fractional payment", "sales", "POST", root + "/payments", {400, 409, 422},
                          json={"amount_paise": 1.5, "method": "UPI"})
            assert minimum > 1, "Seeded order must have a nonzero advance"
            self.data("sales", "POST", root + "/payments", json={"amount_paise": minimum - 1, "method": "UPI"})
            self.negative("R4 one paise short", "sales", "POST", root + "/confirm", {409})
            minimum = 1
        self.data("sales", "POST", root + "/payments", json={"amount_paise": minimum, "method": "UPI"})
        for _ in range(2):
            assert self.data("sales", "POST", root + "/confirm")["status"] == "CONFIRMED"
        deliveries = [r for r in self.rows("warehouse", "deliveries") if r["order_id"] == order["id"]]
        jobs = [r for r in self.rows("director", "installs") if r["order_id"] == order["id"]]
        assert len(deliveries) == len(jobs) == 1, "R5 duplicate or missing job/pick list"
        if check_rules:
            print("PASS Scene 4 repeated confirmation creates exactly one pick and job")
        return order, deliveries[0]["id"], jobs[0]["id"]

    def deliver(self, delivery_id, competing):
        root = f"deliveries/{delivery_id}"
        self.negative("R6 missing scans prevent dispatch", "warehouse", "POST", root + "/dispatch", {409})
        self.negative("R6 incomplete delivery", "warehouse", "POST", root + "/deliver", {409})
        lines = self.data("warehouse", "GET", root)["lines"]
        products = {p["id"]: p for p in self.rows("director", "products")}
        serials = {}
        for line in lines:
            count = line["qty_required"]
            numbers = [f"{self.tag}-{line['sku']}-{i}" for i in range(count)] if line["tracks_serial"] else []
            self.data("warehouse", "POST", "stock/receive", json={"product_id": line["product_id"], "qty": count,
                      "purchase_cost_paise": 100, "serial_numbers": numbers})
            for serial in numbers:
                payload = {"serial_no": serial}
                if not serials:
                    gate = Barrier(2)
                    def scan(_):
                        gate.wait(timeout=10)
                        return self.request("warehouse", "POST", root + "/scan", json=payload)
                    with ThreadPoolExecutor(max_workers=2) as pool:
                        responses = list(pool.map(scan, range(2)))
                    assert sorted(r.status_code for r in responses) == [200, 409], "R7 parallel scan outcomes"
                    error_body(next(r for r in responses if r.status_code == 409))
                    self.negative("R7 duplicate across pick lists", "warehouse", "POST",
                                  f"deliveries/{competing}/scan", {409}, json=payload)
                else:
                    self.data("warehouse", "POST", root + "/scan", json=payload)
                product = products[line["product_id"]]
                expected_terms = {"PANEL": 240, "INVERTER": 24, "BATTERY": 24}
                months = product["warranty_months"]
                if product["category"] in expected_terms:
                    assert months == expected_terms[product["category"]], f"R8 term for {product['category']}"
                serials[serial] = months
        self.data("warehouse", "POST", root + "/dispatch")
        first = next(iter(serials))
        self.negative("R7 dispatched unit", "warehouse", "POST", f"deliveries/{competing}/scan", {409},
                      json={"serial_no": first})
        delivered = self.data("warehouse", "POST", root + "/deliver")
        start = datetime.fromisoformat(delivered["delivered_at"]).date()
        ids = set()
        for serial, months in serials.items():
            warranty = self.data("support", "GET", "lookup", params={"serial": serial})
            assert warranty["in_warranty"] and warranty["start_date"] == start.isoformat()
            assert warranty["end_date"] == (start + relativedelta(months=months)).isoformat()
            ids.add(warranty["warranty_id"])
        assert len(ids) == len(serials) and None not in ids and {24, 240} <= set(serials.values())
        return first

    def install(self, job_id, competing):
        root = f"installs/{job_id}"
        start = self.now - timedelta(hours=1)
        slot = {"crew_lead_id": self.ids["crew"], "crew_ids": [], "scheduled_start": start.isoformat(),
                "scheduled_end": self.now.isoformat()}
        self.data("director", "PATCH", root + "/schedule", json=slot)
        self.negative("R13 overlapping crew slot", "director", "PATCH", f"installs/{competing}/schedule",
                      {409}, json=slot)
        self.data("crew", "POST", root + "/start")
        proof = {"started_at": start.isoformat(), "finished_at": self.now.isoformat(), "system_kw": "3",
                 "signed_by_name": "QA customer", "test_notes": "Generation verified"}
        signature = {"signature": ("signature.png", PNG, "image/png")}
        self.negative("R12 missing site photo", "crew", "POST", root + "/complete", {409}, data=proof, files=signature)
        self.data("crew", "POST", root + "/photos", files={"file": ("roof.png", PNG, "image/png")})
        self.negative("R12 missing signature", "crew", "POST", root + "/complete", {409}, data=proof)
        for key in ("started_at", "finished_at", "system_kw"):
            self.negative("R12 missing " + key, "crew", "POST", root + "/complete", {409},
                          data={k: v for k, v in proof.items() if k != key}, files=signature)
        assert self.data("crew", "POST", root + "/complete", data=proof, files=signature)["status"] == "COMPLETED"
        assert self.data("crew", "POST", root + "/accept")["status"] == "ACCEPTED"

    def ticket(self, serial, covered):
        lookup = self.data("support", "GET", "lookup", params={"serial": serial})
        assert lookup["in_warranty"] is covered
        ticket = self.data("support", "POST", "tickets", json={"serial_no": serial, "fault_code": "OUTPUT",
                           "description": "QA reduced output"})
        assert ticket["billable"] is (not covered)
        root = f"tickets/{ticket['id']}"
        self.data("support", "PATCH", root, json={"status": "IN_PROGRESS"})
        for kind, amount in (("PART", 500), ("LABOUR", 600)):
            self.data("support", "POST", root + "/lines", json={"type": kind, "description": kind,
                      "qty": 1, "unit_price_paise": amount})
        self.data("support", "POST", root + "/resolve", json={"resolution": "Output restored"})
        self.negative("R11 customer must confirm", "support", "POST", root + "/close", {409})
        self.data("support", "POST", root + "/confirm")
        closed = self.data("support", "POST", root + "/close")
        assert closed["ticket"]["status"] == "CLOSED"
        invoices = [r for r in self.rows("director", "invoices") if r.get("ticket_id") == ticket["id"]]
        if covered:
            assert closed["invoice_id"] is None and not invoices, "Covered customer was billed"
        else:
            invoice = self.data("director", "GET", f"invoices/{closed['invoice_id']}")
            assert invoice["ticket_id"] == ticket["id"] and invoice["total_paise"] == 1100
            assert self.data("support", "POST", root + "/close")["invoice_id"] == invoice["id"]

    def workflow(self):
        order, delivery, job = self.order(check_rules=True)
        _, second_delivery, second_job = self.order(check_rules=False)
        serial = self.deliver(delivery, second_delivery)
        print("PASS Scene 5 serial scans and calendar-month warranties")
        self.install(job, second_job)
        print("PASS Scene 6 crew acceptance")
        self.ticket(serial, covered=True)
        print("PASS Scene 8 covered ticket closed at zero charge")
        invoice = self.data("director", "POST", "invoices", json={"order_id": order["id"]})
        assert invoice["total_paise"] == order["total_paise"]
        profits = self.data("director", "GET", "reports/profit-per-job")
        assert any(r["order_id"] == order["id"] and r["revenue_paise"] == invoice["total_paise"] for r in profits)

    def reports(self):
        for period in ("today", "week", "month"):
            summary = self.data("director", "GET", "reports/summary", params={"range": period})
            assert {"revenue_paise", "jobs_unfinished", "open_tickets"} <= summary.keys()
        assert "awaiting_dispatch" in self.data("director", "GET", "reports/unfinished")
        profits = self.data("director", "GET", "reports/profit-per-job")
        assert isinstance(profits, list)
        res = self.request("director", "GET", "reports/export.csv", params={"range": "month"})
        assert res.is_success and "profit_paise" in csv.DictReader(io.StringIO(res.text)).fieldnames


def money_definitions(spec):
    backend = Path(__file__).resolve().parents[1] / "backend"
    sys.path.insert(0, str(backend))
    import app.models_registry  # registers this checkout's ORM models
    from app.core.db import Base
    from pydantic import BaseModel

    for table in Base.metadata.tables.values():
        for col in table.columns:
            if col.name.endswith("_paise"):
                assert col.type.python_type is int, f"R14 {table.name}.{col.name}: {col.type}"
    schemas = dict(spec["components"]["schemas"])
    for path in (backend / "app/modules").glob("*/schemas.py"):
        module = importlib.import_module(f"app.modules.{path.parent.name}.schemas")
        for name, model in vars(module).items():
            if isinstance(model, type) and issubclass(model, BaseModel) and model.__module__ == module.__name__:
                schemas[f"{module.__name__}.{name}"] = model.model_json_schema()
    for name, schema in schemas.items():
        for key, field in schema.get("properties", {}).items():
            if key.endswith("_paise"):
                types = {branch.get("type") for branch in field.get("anyOf", [field])}
                assert "integer" in types and types <= {"integer", "null"}, f"R14 {name}.{key}: {types}"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8100/api/v1")
    parser.add_argument("--expired-serial", default="INV-OLD-2024-001")
    args = parser.parse_args()
    password = os.environ.get("QA_SEED_PASSWORD")
    if not password:
        parser.error("Set QA_SEED_PASSWORD to the throwaway database's demo password.")
    with ExitStack() as stack:
        demo = Demo(args.base_url.rstrip("/") + "/", stack)
        spec = httpx.get(args.base_url.rstrip("/").removesuffix("/api/v1") + "/openapi.json")
        spec.raise_for_status()
        demo.run("R14 registered model and OpenAPI money types", lambda: money_definitions(spec.json()))
        demo.negative("no login", "public", "GET", "auth/me", {401})
        demo.negative("unknown JSON field", "public", "POST", "auth/login", {422},
                      json={"email": "sales@sunpower.test", "password": password, "unexpected": True})
        for role in ROLES:
            demo.run("seeded " + role + " login", lambda role=role: demo.login(role, password))
        for field in ("phone", "pincode"):
            demo.negative("invalid " + field, "public", "POST", "public/enquiries", {422},
                          json={**demo.enquiry(), field: "bad"})
        demo.negative("wrong role", "crew", "GET", "reports/summary", {403})
        demo.run("Scenes 1–6 and covered service", demo.workflow)
        demo.run("Scenes 7–8 seeded expired unit and automatic invoice", lambda: demo.ticket(args.expired_serial, False))
        demo.run("Scene 9 director reports and CSV", demo.reports)
        print(f"{len(demo.failures)} failed checks or blocked scene groups")
        return int(bool(demo.failures))


if __name__ == "__main__":
    sys.exit(main())
