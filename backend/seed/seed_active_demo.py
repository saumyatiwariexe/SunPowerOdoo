"""Add a live demo pipeline, preserving all existing records and demo progress.
Run: python -m seed.seed_active_demo --apply
"""
import argparse
from datetime import UTC, datetime, timedelta
from sqlalchemy import select
from sqlalchemy.orm import Session
import app.models_registry
from app.core.db import get_engine
from app.modules.users.models import User, Customer
from app.modules.leads import service as leads
from app.modules.leads.schemas import NewCustomerLead, LeadCallCreate
from app.modules.surveys import service as surveys
from app.modules.surveys.schemas import SurveySchedule, SurveySubmit
from app.modules.catalog.models import Package, Product
from app.modules.quotes import service as quotes
from app.modules.quotes.schemas import QuoteCreate
from app.modules.orders import service as orders
from app.modules.billing import service as billing
from app.modules.deliveries import service as deliveries
from app.modules.deliveries.models import Delivery, DeliveryLine
from app.modules.inventory import service as inventory
from app.modules.inventory.schemas import StockReceiveIn
from app.modules.installs import service as installs
from app.modules.installs.models import InstallJob
from app.modules.installs.schemas import InstallSchedule, InstallCompletion
from app.modules.tickets import service as tickets
from app.modules.tickets.schemas import TicketCreate, TicketPatch

NAMES = ['Rehan Khan', 'Ananya Verma', 'Gurpreet Singh', 'Meera Kapoor', 'Aman Gupta', 'Simran Kaur', 'Rohit Malhotra', 'Nisha Bansal', 'Harpreet Gill', 'Karan Sethi', 'Pooja Sharma', 'Vikram Arora', 'Neha Sood', 'Arjun Mehta', 'Sana Ali', 'Manpreet Kaur']


def add_active_demo(db):
    staff = {role: db.scalar(select(User).where(User.email == role + '@sunpower.test')) for role in ('sales', 'surveyor', 'warehouse', 'crew', 'support', 'director')}
    if not all(staff.values()):
        raise RuntimeError('Seed the demo users first.')
    package = db.scalar(select(Package).where(Package.active.is_(True), Package.capacity_kw == 3, Package.system_type == 'ON_GRID').order_by(Package.id))
    if not package:
        raise RuntimeError('An active 3 kW on-grid package is required.')
    now = datetime.now(UTC).replace(microsecond=0)
    created = 0
    for stage, name in enumerate(NAMES):
        email = f'active.demo.{stage:02d}@sunpower.invalid'
        if db.scalar(select(Customer.id).where(Customer.email == email)):
            continue
        lead = leads.create_lead(db, NewCustomerLead(name=name, phone=f'988880{stage:04d}', address=f'{42+stage}, Model Town, Jalandhar (demo site)', pincode='144003', requested_kw=3, system_type='ON_GRID', source='CALL', subsidy_interest=True, assigned_to_id=staff['sales'].id, notes='Active demonstration project; fictional customer.'), staff['sales'])
        db.get(Customer, lead.customer_id).email = email
        created += 1
        if stage == 0: continue
        leads.add_call(db, lead.id, LeadCallCreate(outcome='Interested; roof access confirmed', shadow_free_area_sqm=40+stage, monthly_bill_paise=450000+stage*10000, grid_suitable=True, notes='Prefers a morning visit. Call before arrival.', called_at=now), staff['sales'])
        if stage == 1: continue
        survey = surveys.schedule(db, lead.id, SurveySchedule(surveyor_id=staff['surveyor'].id, scheduled_at=now+timedelta(hours=stage) if stage < 4 else now-timedelta(days=3)), staff['sales'])
        if stage in (2,3): continue
        surveys.attach_photo(db, survey, '/solar-array.jpg')
        surveys.submit(db, survey.id, SurveySubmit(roof_direction='South', tilt_degrees=25, cable_distance_m=18+stage, shadow_notes='Clear roof; parapet shadow limited to early morning.'), staff['surveyor'])
        if stage == 4: continue
        surveys.review(db, survey.id, 'Roof and grid connection suitable for 3 kW.', staff['director'], approved=True)
        if stage == 5: continue
        quote = quotes.create_from_package(db, QuoteCreate(lead_id=lead.id, package_id=package.id, valid_until=now.date()+timedelta(days=30)), staff['sales'])
        if stage == 6: continue
        quotes.send(db, quote.id)
        if stage == 7: continue
        order = quotes.accept(db, quote.id)
        if stage == 8: continue
        billing.record_payment(db, order_id=order.id, amount_paise=order.advance_min_paise, user_id=staff['sales'].id, reference='DEMO-ADVANCE')
        orders.confirm(db, order.id)
        delivery = db.scalar(select(Delivery).where(Delivery.order_id == order.id))
        serials = []
        for line in db.scalars(select(DeliveryLine).where(DeliveryLine.delivery_id == delivery.id)):
            product = db.get(Product, line.product_id)
            numbers = [f'DEMO-{stage:02d}-{product.sku}-{i+1:02d}' for i in range(line.qty_required)] if product.tracks_serial else []
            inventory.receive_stock(db, StockReceiveIn(product_id=product.id, qty=line.qty_required, purchase_cost_paise=product.cost_paise, serial_numbers=numbers))
            serials.extend(numbers)
        if stage == 9: continue
        for serial in serials:
            deliveries.scan_serial(db, delivery.id, serial, staff['warehouse'].id)
        deliveries.dispatch(db, delivery.id, vehicle='PB08-DEMO')
        if stage == 10: continue
        deliveries.complete(db, delivery.id, staff['warehouse'].id)
        job = db.scalar(select(InstallJob).where(InstallJob.order_id == order.id))
        slot = now + timedelta(days=stage-11, hours=2) if stage < 13 else now - timedelta(days=stage-13, hours=2)
        installs.schedule(db, job.id, InstallSchedule(crew_lead_id=staff['crew'].id, scheduled_start=slot, scheduled_end=slot+timedelta(hours=4)), )
        if stage in (11,12): continue
        installs.start(db, job.id, staff['crew'])
        job.started_at = now - timedelta(hours=2)
        if stage == 13: continue
        installs.attach_photo(db, job, '/solar-array.jpg', 'Panels mounted and wiring checked')
        installs.complete(db, job, InstallCompletion(started_at=job.started_at, finished_at=now-timedelta(minutes=15), system_kw=3, signed_by_name=name, test_notes='Generation and earthing checked.'), '/sample-signature.svg')
        if stage == 14: continue
        installs.accept(db, job.id, staff['crew'])
        for index, description in enumerate(('Inverter display intermittently switches off', 'Generation reading is lower than expected', 'Monitoring app is not connecting')):
            ticket = tickets.create(db, TicketCreate(serial_no=serials[index % len(serials)], fault_code='PERFORMANCE', description=description, priority='HIGH' if index==0 else 'NORMAL'))
            tickets.update(db, ticket.id, TicketPatch(assigned_to_id=staff['support'].id))
            if index:
                tickets.update(db, ticket.id, TicketPatch(status='IN_PROGRESS'))
            if index == 2:
                tickets.resolve(db, ticket.id, 'Repaired the monitoring connection; awaiting customer confirmation.')
    db.flush()
    return created


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--apply', action='store_true', required=True)
    parser.parse_args()
    with Session(get_engine()) as db, db.begin():
        print('Active demo projects added:', add_active_demo(db))
