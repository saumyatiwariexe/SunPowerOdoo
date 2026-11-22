from datetime import UTC, date, datetime, timedelta
from urllib.error import HTTPError
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
import app.models_registry  # noqa
from app.core.config import Settings, get_settings
from app.core.db import Base, get_db
from app.core.numbering import seed_counters
from app.core.security import create_session_token
from app.main import create_app
from app.modules.portal import auth, service
from app.modules.portal.models import CustomerAccount
from app.modules.users.models import Customer, User
from app.modules.leads.models import Lead
from app.modules.catalog.models import Package, Product
from app.modules.quotes.models import Quote
from app.modules.orders.models import Order
from app.modules.billing.models import Invoice
from app.modules.inventory.models import SerialUnit

PASSWORD = 'customer-test-password'


@pytest.fixture
def portal(monkeypatch):
    engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
    @event.listens_for(engine, 'connect')
    def fk(connection, _):
        connection.execute('PRAGMA foreign_keys=ON')
    Base.metadata.create_all(engine)
    settings = Settings(jwt_secret='z' * 32, sendgrid_api_key='test-only',
                        sendgrid_from_email='sender@example.test', customer_portal_url='https://solar.example.test')
    app = create_app()
    def db_session():
        with Session(engine) as db:
            yield db
    app.dependency_overrides[get_db] = db_session
    app.dependency_overrides[get_settings] = lambda: settings
    with Session(engine) as db:
        seed_counters(db)
        db.add_all([User(id=i, name=role, email=f'{role}@example.test', role=role, password_hash='unused')
                    for i, role in ((1, 'SALES'), (2, 'WAREHOUSE'))])
        # Shared phone deliberately must not grant access to another customer record.
        db.add_all([Customer(id=i, name=str(i), phone='9876543210', address='Test address', pincode='144001') for i in (1, 2)])
        package = Package(name='Test package', price_paise=10000)
        product = Product(sku='PORTAL', name='Inverter', category='INVERTER', unit='unit', cost_paise=100, price_paise=200)
        db.add_all([package, product]); db.flush()
        for i in (1, 2):
            db.add(Lead(id=i, customer_id=i, source='WEB', requested_kw=1, system_type='ON_GRID', status='CONTACTED'))
            db.flush()
            db.add(Quote(id=i, number=f'QT-{i}', lead_id=i, customer_id=i, package_id=package.id,
                         status='SENT', subtotal_paise=10000, total_paise=10000, valid_until=date.today()))
            db.flush()
            db.add(Order(id=i, number=f'ORD-{i}', quote_id=i, customer_id=i, total_paise=10000, advance_min_paise=3000))
            db.flush()
            db.add(Invoice(number=f'INV-{i}', customer_id=i, order_id=i, issued_at=datetime.now(UTC)))
            db.add(SerialUnit(product_id=product.id, serial_no=f'SERIAL-{i}', customer_id=i, status='DISPATCHED'))
        db.commit()
    mail = []
    monkeypatch.setattr(auth, 'send_invite', lambda settings, email, token: mail.append((email, token)))
    with TestClient(app) as client:
        yield client, settings, engine, mail
    app.dependency_overrides.clear()
    engine.dispose()


def staff(client, settings, user_id=1):
    client.cookies.set('sunpower_session', create_session_token(user_id, settings), domain='testserver.local', path='/api/v1')


def onboard(portal):
    client, settings, _, mail = portal
    staff(client, settings)
    assert client.post('/api/v1/customer-management/leads/1/invite', json={'email': 'Client@Example.test'}).status_code == 200
    client.cookies.clear()
    result = client.post('/api/v1/customer/auth/login', json={'email': 'client@example.test', 'password': mail[-1][1]})
    assert result.status_code == 200
    assert 'httponly' in result.headers['set-cookie'].lower()
    return mail[-1][1]


def test_agent_invitation_activation_login_and_isolation(portal):
    client, settings, engine, mail = portal
    assert client.get('/api/v1/customer/overview').status_code == 401
    assert client.post('/api/v1/customer/auth/login', json={'email': 'client@example.test', 'password': PASSWORD}).status_code == 401
    token = onboard(portal)
    with Session(engine) as db:
        account = db.scalar(select(CustomerAccount))
        assert account.password_hash != token and account.invite_hash is None
        assert account.activated_at is not None and account.invite_expires_at is None
    assert client.post('/api/v1/customer/auth/activate', json={'token': 'x' * 32, 'password': PASSWORD}).status_code == 400
    data = client.get('/api/v1/customer/overview').json()['data']
    assert [r['number'] for r in data['quotes']] == ['QT-1']
    assert [r['serial_no'] for r in data['equipment']] == ['SERIAL-1']
    for kind in ('quotes', 'invoices'):
        assert client.get(f'/api/v1/customer/documents/{kind}/1').status_code == 200
        assert client.get(f'/api/v1/customer/documents/{kind}/2').status_code == 404
    assert client.post('/api/v1/customer/tickets', json={'serial_no': 'SERIAL-2', 'description': 'Inverter is broken'}).status_code == 404
    assert client.post('/api/v1/customer/tickets', json={'serial_no': 'SERIAL-1', 'description': 'Inverter is broken'}).status_code == 201
    assert len(client.get('/api/v1/customer/overview').json()['data']['tickets']) == 1
    assert client.get('/api/v1/users').status_code == 401
    customer_token = client.cookies.get(service.COOKIE)
    client.cookies.set('sunpower_session', customer_token, domain='testserver.local', path='/api/v1')
    assert client.get('/api/v1/auth/me').status_code == 401
    client.post('/api/v1/customer/auth/logout')
    assert client.get('/api/v1/customer/overview').status_code == 401
    assert client.post('/api/v1/customer/auth/login', json={'email': 'CLIENT@example.test', 'password': token}).status_code == 200
    assert client.post('/api/v1/customer/auth/login', json={'email': 'client@example.test', 'password': 'wrong'}).status_code == 401


def test_invitation_role_state_resend_expiry_and_duplicate_email(portal):
    client, settings, engine, mail = portal
    path = '/api/v1/customer-management/leads/1/invite'
    payload = {'email': 'client@example.test'}
    assert client.post(path, json=payload).status_code == 401
    staff(client, settings, 2)
    assert client.post(path, json=payload).status_code == 403
    staff(client, settings)
    with Session(engine) as db:
        db.get(Lead, 1).status = 'NEW'; db.commit()
    assert client.post(path, json=payload).status_code == 409
    with Session(engine) as db:
        assert db.scalar(select(CustomerAccount)) is None
        db.get(Lead, 1).status = 'CONTACTED'; db.commit()
    assert client.post(path, json=payload).status_code == 200
    first = mail[-1][1]
    assert client.post(path, json=payload).status_code == 200
    assert client.post('/api/v1/customer/auth/login', json={'email': 'client@example.test', 'password': first}).status_code == 401
    assert client.post('/api/v1/customer-management/leads/2/invite', json=payload).status_code == 409
    with Session(engine) as db:
        account = db.scalar(select(CustomerAccount))
        assert account.invite_hash is None
        from app.core.security import verify_password
        assert verify_password(mail[-1][1], account.password_hash)
        assert not verify_password(first, account.password_hash)
        account.invite_expires_at = datetime.now(UTC) - timedelta(seconds=1); db.commit()
    assert client.post('/api/v1/customer/auth/login', json={'email': 'client@example.test', 'password': mail[-1][1]}).status_code == 401


def test_configuration_drafts_validation_and_rate_limit(portal):
    client, settings, engine, _ = portal
    staff(client, settings)
    settings.sendgrid_api_key = None
    assert client.post('/api/v1/customer-management/leads/1/invite', json={'email': 'client@example.test'}).status_code == 503
    from pydantic import SecretStr
    settings.sendgrid_api_key = SecretStr('test-only')
    onboard(portal)
    with Session(engine) as db:
        db.get(Quote, 1).status = 'DRAFT'; db.commit()
    assert client.get('/api/v1/customer/documents/quotes/1').status_code == 404
    assert client.get('/api/v1/customer/overview').json()['data']['quotes'] == []
    assert client.post('/api/v1/customer/tickets', json={'serial_no': 'SERIAL-1', 'description': 'Inverter is broken', 'customer_id': 2}).status_code == 422
    responses = [client.post('/api/v1/customer/auth/login', json={'email': 'nobody@example.test', 'password': 'wrong'}) for _ in range(11)]
    assert responses[-1].status_code == 429


def test_sendgrid_payload_and_failure(portal, monkeypatch):
    import json
    # Test the actual transport separately from the route's mocked email sender.
    from importlib import reload
    reload(auth)
    client, settings, engine, _ = portal
    requests = []
    class Accepted:
        status = 202
        def __enter__(self): return self
        def __exit__(self, *args): pass
    monkeypatch.setattr(auth, 'urlopen', lambda req, timeout: (requests.append(req), Accepted())[1])
    auth.send_invite(settings, 'client@example.test', 'one-time-token')
    payload = json.loads(requests[0].data)
    assert payload['personalizations'][0]['to'][0]['email'] == 'client@example.test'
    assert 'Sign in: https://solar.example.test/customer' in payload['content'][0]['value']
    assert 'Password: one-time-token' in payload['content'][0]['value']
    assert '/activate' not in payload['content'][0]['value']
    assert payload['tracking_settings']['click_tracking']['enable'] is False
    def fail(*args, **kwargs): raise HTTPError('https://api.sendgrid.com', 403, 'Denied', {}, None)
    monkeypatch.setattr(auth, 'urlopen', fail)
    staff(client, settings)
    result = client.post('/api/v1/customer-management/leads/1/invite', json={'email': 'client@example.test'})
    assert result.status_code == 503
    with Session(engine) as db:
        assert db.scalar(select(CustomerAccount)).activated_at is None


def test_generated_password_is_private_and_existing_accounts_are_unchanged(portal):
    client, settings, engine, mail = portal
    staff(client, settings)
    path = '/api/v1/customer-management/leads/1/invite'
    result = client.post(path, json={'email': 'client@example.test'})
    assert result.status_code == 200
    password = mail[-1][1]
    assert len(password) >= 24
    assert password not in result.text
    assert password not in client.get('/api/v1/customer-management/leads/1').text
    with Session(engine) as db:
        account = db.scalar(select(CustomerAccount))
        assert account.activated_at is None
        assert account.password_hash != password
    assert client.post('/api/v1/customer/auth/login', json={'email': 'client@example.test', 'password': password}).status_code == 200
    assert client.post(path, json={'email': 'client@example.test'}).status_code == 409
    assert client.post('/api/v1/customer/auth/login', json={'email': 'client@example.test', 'password': password}).status_code == 200
    settings.customer_portal_url = 'http://localhost:5173'
    status = client.get('/api/v1/customer-management/leads/1').json()['data']
    assert status['local_only'] is True
    assert status['login_url'] == 'http://localhost:5173/customer'


def test_existing_activation_link_still_works(portal):
    import hashlib
    client, settings, engine, mail = portal
    token = 'legacy-invitation-token-' + 'x' * 32
    with Session(engine) as db, db.begin():
        db.add(CustomerAccount(customer_id=1, email='legacy@example.test', invited_by_id=1,
            invite_hash=hashlib.sha256(token.encode()).hexdigest(), invite_expires_at=datetime.now(UTC) + timedelta(hours=1)))
    assert client.post('/api/v1/customer/auth/activate', json={'token': token, 'password': PASSWORD}).status_code == 200
    assert client.post('/api/v1/customer/auth/activate', json={'token': token, 'password': PASSWORD}).status_code == 400
    assert client.get('/api/v1/customer/overview').status_code == 200


def test_customer_accepts_owned_quote_once_and_checks_state(portal):
    from sqlalchemy import func
    client, _, engine, _ = portal
    path = '/api/v1/customer/quotes/1/accept'
    assert client.post(path, json={'accepted': True}).status_code == 401
    onboard(portal)
    assert client.post('/api/v1/customer/quotes/2/accept', json={'accepted': True}).status_code == 404
    assert client.post(path, json={'accepted': False}).status_code == 400
    with Session(engine) as db:
        # Remove the fixture's pre-existing order to exercise actual conversion.
        db.delete(db.scalar(select(Invoice).where(Invoice.order_id == 1)))
        db.delete(db.get(Order, 1)); db.commit()
    first = client.post(path, json={'accepted': True})
    assert first.status_code == 200
    assert first.json()['data']['advance_min_paise'] == 3000
    assert client.post(path, json={'accepted': True}).json() == first.json()
    with Session(engine) as db:
        assert db.get(Quote, 1).status == 'ACCEPTED'
        assert db.scalar(select(func.count()).select_from(Order).where(Order.quote_id == 1)) == 1
        db.get(Quote, 1).status = 'SENT'
        db.get(Quote, 1).valid_until = date.today() - timedelta(days=1)
        db.commit()
    assert client.post(path, json={'accepted': True}).status_code == 409
    with Session(engine) as db:
        db.get(Quote, 1).status = 'DRAFT'; db.commit()
    assert client.post(path, json={'accepted': True}).status_code == 409


def test_payment_report_requires_staff_verification_and_is_idempotent(portal):
    from app.modules.billing.models import Payment
    from app.modules.portal.models import CustomerPaymentReport
    client, settings, engine, _ = portal
    path = '/api/v1/customer/orders/1/payment-reports'
    payload = {'amount_paise': 3000, 'method': 'UPI', 'reference': 'test-utr-001'}
    assert client.post(path, json=payload).status_code == 401
    onboard(portal)
    assert client.post('/api/v1/customer/orders/2/payment-reports', json=payload).status_code == 404
    assert client.get('/api/v1/customer/orders/2/payment-reports').status_code == 404
    for invalid, status in (({**payload, 'amount_paise': 30.5}, 400), ({**payload, 'customer_id': 2}, 422), ({**payload, 'reference': '   '}, 400)):
        assert client.post(path, json=invalid).status_code == status
    result = client.post(path, json=payload)
    assert result.status_code == 201
    report_id = result.json()['data']['id']
    assert client.post(path, json=payload).status_code == 409
    summary = client.get(path).json()['data']
    assert summary['paid_paise'] == 0 and summary['pending_paise'] == 3000
    assert client.get('/api/v1/customer/invoices/1/payment-reports').json()['data']['reports'][0]['id'] == report_id
    review = f'/api/v1/customer-management/payment-reports/{report_id}/review'
    decision = {'decision': 'VERIFIED', 'note': 'Confirmed in bank statement'}
    assert client.post(review, json=decision).status_code == 401
    staff(client, settings, 2)
    assert client.post(review, json=decision).status_code == 403
    staff(client, settings)
    assert client.post('/api/v1/orders/1/confirm').status_code == 409
    assert client.post(review, json=decision).status_code == 200
    assert client.post(review, json=decision).status_code == 200
    assert client.post(review, json={'decision': 'REJECTED', 'note': 'Changed mind'}).status_code == 409
    with Session(engine) as db:
        payments = list(db.scalars(select(Payment)))
        assert len(payments) == 1 and payments[0].received_by_id == 1
        assert db.get(CustomerPaymentReport, report_id).payment_id == payments[0].id
    summary = client.get(path).json()['data']
    assert summary['paid_paise'] == 3000 and summary['pending_paise'] == 0
    assert client.post(path, json={**payload, 'reference': 'other', 'amount_paise': 7001}).status_code == 409
    result = client.post(path, json={**payload, 'reference': 'failed-utr'})
    assert result.status_code == 201
    rejection = f"/api/v1/customer-management/payment-reports/{result.json()['data']['id']}/review"
    assert client.post(rejection, json={'decision': 'REJECTED', 'note': 'Not received'}).status_code == 200
    assert client.get(path).json()['data']['paid_paise'] == 3000
    assert client.get(path).json()['data']['pending_paise'] == 0


def test_standalone_invoice_report_and_existing_staff_payment_guard(portal):
    from app.modules.billing.service import record_payment
    from app.modules.tickets.models import Ticket
    client, settings, engine, _ = portal
    onboard(portal)
    with Session(engine) as db:
        ticket = Ticket(number='TKT-PAYMENT', customer_id=1, serial_unit_id=1,
                        fault_code='OTHER', description='Out of warranty repair', billable=True)
        db.add(ticket); db.flush()
        invoice = db.scalar(select(Invoice).where(Invoice.customer_id == 1))
        invoice.order_id = None; invoice.ticket_id = ticket.id; invoice.total_paise = 5000; db.commit()
    path = '/api/v1/customer/invoices/1/payment-reports'
    result = client.post(path, json={'amount_paise': 2000, 'method': 'BANK', 'reference': 'invoice-bank-1'})
    assert result.status_code == 201
    staff(client, settings)
    review = f"/api/v1/customer-management/payment-reports/{result.json()['data']['id']}/review"
    with Session(engine) as db:
        record_payment(db, invoice_id=1, amount_paise=2000, method='BANK', reference='invoice-bank-1', user_id=1)
        db.commit()
    result = client.post(review, json={'decision': 'VERIFIED', 'note': 'Already received'})
    assert result.status_code == 409 and result.json()['error']['code'] == 'PAYMENT_ALREADY_RECORDED'
    assert client.get(path).json()['data']['paid_paise'] == 2000


def test_customer_order_shows_installation_only_after_verified_advance_and_confirmation(portal):
    client, settings, _, _ = portal
    onboard(portal)
    before = client.get('/api/v1/customer/overview').json()['data']['orders'][0]
    assert before['status'] == 'DRAFT' and before['installation'] is None
    assert before['delivery'] is None and before['invoice_id'] == 1
    report = client.post('/api/v1/customer/orders/1/payment-reports', json={
        'amount_paise': 3000, 'method': 'UPI', 'reference': 'install-advance-1'})
    assert report.status_code == 201
    staff(client, settings)
    assert client.post('/api/v1/orders/1/confirm').status_code == 409
    assert client.post(f"/api/v1/customer-management/payment-reports/{report.json()['data']['id']}/review",
                       json={'decision': 'VERIFIED', 'note': 'Bank receipt checked'}).status_code == 200
    assert client.post('/api/v1/orders/1/confirm').status_code == 200
    after = client.get('/api/v1/customer/overview').json()['data']['orders'][0]
    assert after['status'] == 'CONFIRMED' and after['installation']['status'] == 'SCHEDULED'
    assert after['delivery']['status'] == 'PENDING' and after['delivery_id'] is not None
