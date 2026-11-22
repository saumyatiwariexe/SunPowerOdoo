"""Add 300 connected sample workflows to the configured database.

Run from backend/ with SAMPLE_DATA_PASSWORD set:
    python -m seed.seed_sample_data --apply

This seed is additive and idempotent. It never deletes existing records.
"""

import argparse
import os
from collections import Counter as Tally
from datetime import UTC, datetime, timedelta

from dateutil.relativedelta import relativedelta
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from app.modules.portal.seed import seed_sample_accounts
from app.modules.portal.models import CustomerPaymentReport

import app.models_registry  # noqa: F401
from app.core.db import Base, get_engine
from app.core.numbering import Counter, seed_counters
from app.core.security import hash_password
from app.modules.billing.models import Invoice, InvoiceLine, Payment
from app.modules.catalog.models import Package, PackageItem, Product, ProductCategory, SystemType
from app.modules.deliveries.models import Delivery, DeliveryLine, DeliveryScan
from app.modules.installs.models import InstallCrew, InstallJob, InstallStatus, JobPhoto
from app.modules.inventory.models import SerialUnit, StockMovement
from app.modules.leads.models import Lead, LeadCall, LeadSource, LeadStatus, SystemType as LeadSystemType
from app.modules.orders.models import Order, OrderStatus
from app.modules.quotes.models import Quote, QuoteLine, QuoteStatus
from app.modules.subsidy.models import SubsidyClaim, SubsidyStatus
from app.modules.surveys.models import Survey, SurveyPhoto, SurveyStatus
from app.modules.tickets.models import Ticket, TicketLine, TicketLineType, TicketPriority, TicketStatus
from app.modules.users.models import Customer, Role, User, UserRoleGrant
from app.modules.warranty.models import Warranty

TARGET = 300
SAMPLE_EMAIL = "sample.staff.001@sunpower.invalid"
STAFF_ROLES = (Role.SALES, Role.SURVEYOR, Role.WAREHOUSE, Role.CREW, Role.SUPPORT)
NAMES = ("Aditi Sharma", "Arjun Mehta", "Neha Iyer", "Rohan Singh", "Priya Nair", "Kabir Patel")
SITE_PHOTO = "/solar-array.jpg"
SIGNATURE = "/sample-signature.svg"


def counts(db: Session) -> dict[str, int]:
    return {table.name: db.scalar(select(func.count()).select_from(table)) or 0
            for table in Base.metadata.sorted_tables}


def seed_sample_payment_reports(db: Session) -> None:
    existing = set(db.scalars(select(CustomerPaymentReport.reference).where(
        CustomerPaymentReport.reference.like("SMP-PAY-%"))))
    rows = db.execute(select(Payment, Order).join(Order, Order.id == Payment.order_id)
                      .where(Payment.reference.like("SMP-PAY-%"))).all()
    for payment, order in rows:
        if payment.reference not in existing:
            db.add(CustomerPaymentReport(customer_id=order.customer_id, order_id=order.id,
                amount_paise=payment.amount_paise, method=payment.method,
                reference=payment.reference, status="VERIFIED", payment_id=payment.id,
                reviewed_by_id=payment.received_by_id,
                review_note="Confirmed in sample bank ledger"))
    db.flush()


def delivery_time(i: int, now: datetime) -> datetime:
    return now - (relativedelta(months=27) + timedelta(days=i) if i % 3 == 0
                  else timedelta(days=TARGET + 1 - i))


def add_sample_data(db: Session, password: str) -> dict[str, int]:
    """Insert one coherent 300-job cohort, or verify a previously inserted cohort."""
    if db.scalar(select(User.id).where(User.email == SAMPLE_EMAIL)) is not None:
        now = datetime.now(UTC).replace(microsecond=0)
        for package in db.scalars(select(Package).where(Package.name.like("Sample On-Grid %"))):
            package.active = False
        sample_leads = db.execute(select(Lead, Customer.email).join(Customer).where(
            Customer.email.like("sample.customer.%@sunpower.invalid"))).all()
        for lead, email in sample_leads:
            index = int(email.split(".")[2].split("@")[0])
            if lead.created_at > now - timedelta(days=10):
                lead.created_at = delivery_time(index, now) - timedelta(days=10)
        db.flush()
        seed_sample_accounts(db, password)
        seed_sample_payment_reports(db)
        result = counts(db)
        short = {name: count for name, count in result.items() if count < TARGET}
        if short:
            raise RuntimeError(f"Existing sample cohort is incomplete: {short}")
        return result

    now = datetime.now(UTC).replace(microsecond=0)
    password_hash = hash_password(password)
    seed_counters(db)

    director = db.scalar(select(User).where(User.role == Role.DIRECTOR, User.active.is_(True)).limit(1))
    if director is None:
        director = User(name="Sample Director", email="sample.director@sunpower.invalid",
                        role=Role.DIRECTOR, password_hash=password_hash, active=True)
        db.add(director)

    staff = [
        User(name=f"Sample {NAMES[(i - 1) % len(NAMES)]} {i:03d}",
             email=f"sample.staff.{i:03d}@sunpower.invalid", password_hash=password_hash,
             role=STAFF_ROLES[(i - 1) % len(STAFF_ROLES)], active=True,
             hourly_rate_paise=18_000 + (i % 5) * 2_000,
             role_grants=[UserRoleGrant(role=STAFF_ROLES[i % len(STAFF_ROLES)])])
        for i in range(1, TARGET + 1)
    ]
    panel = Product(sku="SMP-PANEL-500", name="Sample 500 W panel", category=ProductCategory.PANEL,
                    unit="unit", tracks_serial=True, warranty_months=240,
                    cost_paise=720_000, price_paise=950_000, on_hand=TARGET)
    inverter = Product(sku="SMP-INVERTER", name="Sample hybrid inverter", category=ProductCategory.INVERTER,
                       unit="unit", tracks_serial=True, warranty_months=24,
                       cost_paise=2_200_000, price_paise=3_100_000, on_hand=TARGET)
    installation = Product(sku="SMP-INSTALLATION", name="Sample installation service",
                           category=ProductCategory.SERVICE, unit="job", tracks_serial=False,
                           cost_paise=400_000, price_paise=650_000, on_hand=0)
    extra_categories = (ProductCategory.STAND, ProductCategory.WIRING, ProductCategory.SAFETY)
    extras = [
        Product(sku=f"SMP-KIT-{i:03d}", name=f"Sample roof and safety kit {i:03d}",
                category=extra_categories[(i - 1) % len(extra_categories)], unit="kit",
                tracks_serial=False, cost_paise=70_000 + i * 100,
                price_paise=110_000 + i * 150, on_hand=0)
        for i in range(1, TARGET - 2)
    ]
    customers = [
        Customer(name=f"Sample {NAMES[(i + 1) % len(NAMES)]} {i:03d}",
                 phone=f"9000{i:06d}", email=f"sample.customer.{i:03d}@sunpower.invalid",
                 address=f"Sample rooftop site {i}, Sector {i % 40 + 1}", city="Jalandhar", pincode="144001")
        for i in range(1, TARGET + 1)
    ]
    db.add_all([director, *staff, panel, inverter, installation, *extras, *customers])
    db.flush()

    packages = []
    leads = []
    for i, customer in enumerate(customers, 1):
        kw = (i - 1) % 5 + 1
        extra = extras[(i - 1) % len(extras)]
        package = Package(name=f"Sample On-Grid {kw} kW / {i:03d}", system_type=SystemType.ON_GRID,
                          capacity_kw=kw, price_paise=2 * kw * panel.price_paise + inverter.price_paise
                          + installation.price_paise + extra.price_paise, active=False)
        lead = Lead(customer_id=customer.id, source=(LeadSource.WEB, LeadSource.WHATSAPP,
                    LeadSource.CALL)[(i - 1) % 3], requested_kw=float(kw),
                    system_type=LeadSystemType.ON_GRID, subsidy_interest=True,
                    status=LeadStatus.WON, assigned_to_id=staff[(i - 1) // 5 * 5].id,
                    notes="Sample completed solar enquiry",
                    created_at=delivery_time(i, now) - timedelta(days=10))
        packages.append(package)
        leads.append(lead)
    db.add_all([*packages, *leads])
    db.flush()

    surveys = []
    quotes = []
    delivery_times = []
    for i, (customer, lead, package) in enumerate(zip(customers, leads, packages), 1):
        kw = package.capacity_kw
        extra = extras[(i - 1) % len(extras)]
        delivered_at = delivery_time(i, now)
        delivery_times.append(delivered_at)
        sales = staff[((i - 1) // 5) * 5]
        surveyor = staff[((i - 1) // 5) * 5 + 1]
        db.add_all([
            PackageItem(package_id=package.id, product_id=product.id, qty=qty)
            for product, qty in ((panel, 2 * kw), (inverter, 1), (installation, 1), (extra, 1))
        ])
        db.add(LeadCall(lead_id=lead.id, called_by_id=sales.id,
                        shadow_free_area_sqm=float(kw * 12), monthly_bill_paise=kw * 120_000,
                        grid_suitable=True, outcome="Site visit and quote accepted",
                        called_at=delivered_at - timedelta(days=10)))
        survey = Survey(lead_id=lead.id, surveyor_id=surveyor.id,
                        scheduled_at=delivered_at - timedelta(days=8), roof_direction="South",
                        tilt_degrees=22.0, cable_distance_m=12.0,
                        shadow_notes="Clear roof for sample installation",
                        review_note="Approved for sample quote", status=SurveyStatus.APPROVED,
                        approved_by_id=director.id, approved_at=delivered_at - timedelta(days=7),
                        photos=[SurveyPhoto(url=SITE_PHOTO)])
        parts = ((panel, 2 * kw), (inverter, 1), (installation, 1), (extra, 1))
        quote = Quote(number=f"QT-SMP-{i:04d}", lead_id=lead.id, customer_id=customer.id,
                      package_id=package.id, status=QuoteStatus.ACCEPTED,
                      subtotal_paise=package.price_paise, subsidy_paise=0,
                      total_paise=package.price_paise,
                      valid_until=delivered_at.date() + timedelta(days=30),
                      lines=[QuoteLine(product_id=product.id, description=product.name,
                                       qty=qty, unit_price_paise=product.price_paise,
                                       line_paise=qty * product.price_paise)
                             for product, qty in parts])
        surveys.append(survey)
        quotes.append(quote)
    db.add_all([*surveys, *quotes])
    db.flush()

    orders = [
        Order(number=f"ORD-SMP-{i:04d}", quote_id=quote.id, customer_id=customer.id,
              status=OrderStatus.INSTALLED, total_paise=quote.total_paise,
              advance_min_paise=(quote.total_paise * 30 + 99) // 100,
              confirmed_at=delivery_times[i - 1] - timedelta(days=3))
        for i, (quote, customer) in enumerate(zip(quotes, customers), 1)
    ]
    db.add_all(orders)
    db.flush()

    deliveries = []
    installs = []
    invoices = []
    for i, (order, customer, delivered_at) in enumerate(zip(orders, customers, delivery_times), 1):
        crew = staff[((i - 1) // 5) * 5 + 3]
        warehouse = staff[((i - 1) // 5) * 5 + 2]
        deliveries.append(Delivery(order_id=order.id, status="DELIVERED",
                                   vehicle=f"PB-08-SMP-{i:04d}",
                                   dispatched_at=delivered_at - timedelta(hours=5),
                                   delivered_at=delivered_at, delivered_by_id=warehouse.id))
        installs.append(InstallJob(order_id=order.id, crew_lead_id=crew.id,
                                   scheduled_start=delivered_at + timedelta(days=1),
                                   scheduled_end=delivered_at + timedelta(days=1, hours=6),
                                   started_at=delivered_at + timedelta(days=1),
                                   finished_at=delivered_at + timedelta(days=1, hours=5),
                                   system_kw=float(packages[i - 1].capacity_kw),
                                   test_notes="Sample generation test passed",
                                   status=InstallStatus.ACCEPTED,
                                   signed_by_name=customer.name, signature_url=SIGNATURE,
                                   accepted_at=delivered_at + timedelta(days=1, hours=6)))
        invoices.append(Invoice(number=f"INV-SMP-{i:04d}", order_id=order.id,
                                customer_id=customer.id, status="PAID",
                                total_paise=order.total_paise, paid_paise=order.total_paise,
                                issued_at=delivered_at - timedelta(days=2)))
        db.add(SubsidyClaim(order_id=order.id, scheme="PM Surya Ghar",
                            status=(SubsidyStatus.SUBMITTED, SubsidyStatus.APPROVED,
                                    SubsidyStatus.PAID)[(i - 1) % 3],
                            amount_paise=3_000_000, reference_no=f"SMP-SUB-{i:04d}"))
    db.add_all([*deliveries, *installs, *invoices])
    db.flush()

    total_panels = sum(2 * package.capacity_kw for package in packages)
    db.add_all([
        StockMovement(product_id=panel.id, qty=total_panels + TARGET,
                      reason="PURCHASE", ref_type="SAMPLE", cost_paise=panel.cost_paise),
        StockMovement(product_id=inverter.id, qty=TARGET * 2,
                      reason="PURCHASE", ref_type="SAMPLE", cost_paise=inverter.cost_paise),
    ])
    extra_usage = Tally(extras[(i - 1) % len(extras)].id for i in range(1, TARGET + 1))
    db.add_all(StockMovement(product_id=extra.id, qty=extra_usage[extra.id],
                             reason="PURCHASE", ref_type="SAMPLE", cost_paise=extra.cost_paise)
               for extra in extras)

    serials = []
    serial_refs = []
    for i, (order, delivery, install, invoice, customer, package, delivered_at) in enumerate(
        zip(orders, deliveries, installs, invoices, customers, packages, delivery_times), 1
    ):
        kw = package.capacity_kw
        extra = extras[(i - 1) % len(extras)]
        crew = staff[((i - 1) // 5) * 5 + 3]
        warehouse = staff[((i - 1) // 5) * 5 + 2]
        sales = staff[((i - 1) // 5) * 5]
        db.add_all([
            DeliveryLine(delivery_id=delivery.id, product_id=product.id,
                         qty_required=qty, qty_packed=qty)
            for product, qty in ((panel, 2 * kw), (inverter, 1), (extra, 1))
        ])
        db.add_all([
            StockMovement(product_id=product.id, qty=-qty, reason="DISPATCH",
                          ref_type="DELIVERY", ref_id=delivery.id, cost_paise=product.cost_paise)
            for product, qty in ((panel, 2 * kw), (inverter, 1), (extra, 1))
        ])
        db.add(InstallCrew(install_job_id=install.id, user_id=crew.id))
        db.add(JobPhoto(install_job_id=install.id, url=SITE_PHOTO,
                        caption="Sample completed installation", taken_at=delivered_at + timedelta(days=1)))
        db.add(InvoiceLine(invoice_id=invoice.id, description=f"Sample rooftop installation {order.number}",
                           qty=1, unit_price_paise=order.total_paise))
        db.add(Payment(order_id=order.id, invoice_id=invoice.id,
                       amount_paise=order.total_paise, method="BANK",
                       reference=f"SMP-PAY-{i:04d}", paid_at=delivered_at - timedelta(days=2),
                       received_by_id=sales.id))
        for j in range(1, 2 * kw + 1):
            serial = SerialUnit(product_id=panel.id, serial_no=f"SMP-P-{i:04d}-{j:02d}",
                                status="INSTALLED", purchase_cost_paise=panel.cost_paise,
                                delivery_id=delivery.id, customer_id=customer.id,
                                installed_at=delivered_at + timedelta(days=1))
            serials.append(serial)
            serial_refs.append((i, serial, panel, order, delivery, customer, warehouse, delivered_at))
        serial = SerialUnit(product_id=inverter.id, serial_no=f"SMP-I-{i:04d}",
                            status="INSTALLED", purchase_cost_paise=inverter.cost_paise,
                            delivery_id=delivery.id, customer_id=customer.id,
                            installed_at=delivered_at + timedelta(days=1))
        serials.append(serial)
        serial_refs.append((i, serial, inverter, order, delivery, customer, warehouse, delivered_at))
    serials.extend(SerialUnit(product_id=panel.id, serial_no=f"SMP-P-STOCK-{i:04d}",
                              purchase_cost_paise=panel.cost_paise) for i in range(1, TARGET + 1))
    serials.extend(SerialUnit(product_id=inverter.id, serial_no=f"SMP-I-STOCK-{i:04d}",
                              purchase_cost_paise=inverter.cost_paise) for i in range(1, TARGET + 1))
    db.add_all(serials)
    db.flush()

    warranties = []
    ticket_serials = {}
    for i, serial, product, order, delivery, customer, warehouse, delivered_at in serial_refs:
        warranty_end = delivered_at.date() + relativedelta(months=product.warranty_months)
        warranty = Warranty(serial_unit_id=serial.id, customer_id=customer.id, order_id=order.id,
                            start_date=delivered_at.date(), end_date=warranty_end,
                            status="ACTIVE" if warranty_end >= now.date() else "EXPIRED")
        warranties.append(warranty)
        db.add(DeliveryScan(delivery_id=delivery.id, serial_unit_id=serial.id,
                            scanned_by_id=warehouse.id, scanned_at=delivered_at - timedelta(hours=6)))
        if (product == inverter and i % 2 == 1) or (product == panel and i % 2 == 0
                                                     and i not in ticket_serials):
            ticket_serials[i] = (serial, warranty)
    db.add_all(warranties)
    db.flush()

    for i, (customer, delivered_at) in enumerate(zip(customers, delivery_times), 1):
        serial, warranty = ticket_serials[i]
        billable = warranty.status == "EXPIRED"
        closed = not billable and i % 4 == 0
        db.add(Ticket(number=f"TKT-SMP-{i:04d}", customer_id=customer.id,
                      serial_unit_id=serial.id, warranty_id=warranty.id,
                      fault_code="SAMPLE_CHECK", description="Sample system inspection request",
                      priority=(TicketPriority.LOW, TicketPriority.NORMAL, TicketPriority.HIGH)[i % 3],
                      status=TicketStatus.CLOSED if closed else TicketStatus.OPEN,
                      assigned_to_id=staff[((i - 1) // 5) * 5 + 4].id,
                      resolution="Sample inspection completed" if closed else None,
                      customer_confirmed_at=delivered_at + timedelta(days=7) if closed else None,
                      billable=billable,
                      lines=[TicketLine(type=TicketLineType.LABOUR, product_id=None,
                                        description="Sample inspection labour", qty=1,
                                        unit_price_paise=25_000 if billable else 0)]))

    existing_names = set(db.scalars(select(Counter.name)))
    next_counter = 1
    while len(existing_names) < TARGET:
        name = f"SMP{next_counter:04d}"
        next_counter += 1
        if name not in existing_names:
            db.add(Counter(name=name, value=0))
            existing_names.add(name)
    db.flush()

    seed_sample_accounts(db, password)
    seed_sample_payment_reports(db)
    result = counts(db)
    short = {name: count for name, count in result.items() if count < TARGET}
    if short:
        raise RuntimeError(f"Sample cohort did not reach {TARGET} rows: {short}")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Add sample rows to the configured database")
    args = parser.parse_args()
    if not args.apply:
        parser.error("pass --apply after selecting the intended DATABASE_URL")
    password = os.environ.get("SAMPLE_DATA_PASSWORD")
    if not password:
        parser.error("set SAMPLE_DATA_PASSWORD for the synthetic staff accounts")
    engine = get_engine()
    Base.metadata.create_all(engine)
    with Session(engine) as db, db.begin():
        result = add_sample_data(db, password)
    print(f"Sample data ready in {engine.url.render_as_string(hide_password=True)}")
    for name, count in sorted(result.items()):
        print(f"{name}: {count}")


if __name__ == "__main__":
    main()
