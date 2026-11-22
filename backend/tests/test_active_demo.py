from sqlalchemy import create_engine, select, event, func
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient
import app.models_registry
from app.core.db import Base, get_db
from app.core.config import Settings, get_settings
from app.core.numbering import seed_counters
from app.core.security import create_session_token
from app.main import create_app
from seed.seed_users import seed_users
from seed.seed_catalog import seed_catalog
from seed.seed_active_demo import add_active_demo
from app.modules.users.models import User
from app.modules.installs.models import InstallJob


def test_active_work_is_assigned_and_lookup_ticket_chain_works():
    engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
    @event.listens_for(engine, 'connect')
    def foreign_keys(connection, _):
        connection.execute('PRAGMA foreign_keys=ON')
    Base.metadata.create_all(engine)
    with Session(engine) as db, db.begin():
        seed_counters(db)
        seed_users(db, password='throwaway-test-password')
        seed_catalog(db)
        assert add_active_demo(db) == 16
        assert add_active_demo(db) == 0
        users = {u.role: u.id for u in db.scalars(select(User))}
        assert db.scalar(select(func.count()).select_from(InstallJob).where(InstallJob.status == 'IN_PROGRESS')) == 1
    app = create_app()
    settings = Settings(jwt_secret='test-secret-for-demo' * 3)
    def session():
        with Session(engine) as db:
            yield db
    app.dependency_overrides[get_db] = session
    app.dependency_overrides[get_settings] = lambda: settings
    with TestClient(app) as client:
        def login(role):
            client.cookies.set('sunpower_session', create_session_token(users[role], settings), domain='testserver.local', path='/api/v1')
        login('CREW')
        rows = client.get('/api/v1/installs/mine?status=SCHEDULED').json()['data']
        assert len(rows) == 2 and rows[0]['customer_name'] and rows[0]['site_address']
        login('SURVEYOR')
        rows = client.get('/api/v1/surveys/mine?status=SCHEDULED').json()['data']
        assert len(rows) == 2 and rows[0]['customer_phone']
        assert client.get('/api/v1/lookup/search').status_code == 403
        login('WAREHOUSE')
        pending = client.get('/api/v1/deliveries?status=PENDING').json()['data']
        delivery_path = '/api/v1/deliveries/' + str(pending[0]['id'])
        detail = client.get(delivery_path).json()['data']
        candidate = next(line['available_serials'][0] for line in detail['lines'] if line['available_serials'])
        assert client.post(delivery_path + '/scan', json={'serial_no': candidate}).status_code == 200
        assert client.post(delivery_path + '/scan', json={'serial_no': candidate}).status_code == 409
        detail = client.get(delivery_path).json()['data']
        assert all(candidate not in line['available_serials'] for line in detail['lines'])
        login('SUPPORT')
        found = client.get('/api/v1/lookup/search?q=Manpreet&assigned_only=true').json()['data']
        assert found and found[0]['customer_name'] == 'Manpreet Kaur'
        serial = found[0]['serial_no']
        support_queue = client.get('/api/v1/tickets?mine=true').json()
        assert support_queue['meta']['total'] == 3
        assert all(t['assigned_to_id'] == users['SUPPORT'] for t in support_queue['data'])
        login('DIRECTOR')
        assert client.get('/api/v1/tickets?mine=true').json()['meta']['total'] == 0
        options = client.get('/api/v1/auth/assignment-options').json()['data']
        assert users['DIRECTOR'] in [u['id'] for u in options]
        owned = client.post('/api/v1/tickets', json={'serial_no': serial, 'fault_code': 'MONITORING', 'description': 'Director owned repair', 'assigned_to_id': users['DIRECTOR']})
        assert owned.status_code == 201
        owned_id = owned.json()['data']['id']
        assert owned.json()['data']['assigned_to_name']
        queue = client.get('/api/v1/tickets', params={'mine': 'true', 'assigned_to_id': users['SUPPORT'], 'status': 'OPEN'}).json()
        assert [t['id'] for t in queue['data']] == [owned_id]
        moved = client.patch(f'/api/v1/tickets/{owned_id}', json={'assigned_to_id': users['SUPPORT']})
        assert moved.status_code == 200 and moved.json()['data']['assigned_to_name'] != owned.json()['data']['assigned_to_name']
        assert client.get('/api/v1/tickets?mine=true').json()['meta']['total'] == 0
        login('SUPPORT')
        assert client.get('/api/v1/tickets?mine=true').json()['meta']['total'] == 4
        assert client.patch(f'/api/v1/tickets/{owned_id}', json={'assigned_to_id': None}).status_code == 200
        assert client.get('/api/v1/tickets?mine=true').json()['meta']['total'] == 3
        total = client.get('/api/v1/tickets').json()['meta']['total']
        invalid = client.post('/api/v1/tickets', json={'serial_no': serial, 'fault_code': 'MONITORING', 'description': 'Invalid assignee', 'assigned_to_id': users['SALES']})
        assert invalid.status_code == 409
        assert client.get('/api/v1/tickets').json()['meta']['total'] == total
        assert client.get('/api/v1/lookup', params={'serial': serial.lower()}).status_code == 200
        assert client.get('/api/v1/lookup', params={'phone': '+91 9888800015'}).json()['data']
        created = client.post('/api/v1/tickets', json={'serial_no': serial, 'fault_code': 'MONITORING', 'description': 'Monitoring app cannot connect'})
        assert created.status_code == 201
        path = '/api/v1/tickets/' + str(created.json()['data']['id'])
        assert client.patch(path, json={'description': 'Gateway disconnects every evening', 'fault_code': 'GATEWAY'}).status_code == 200
        assert client.get(path).json()['data']['description'] == 'Gateway disconnects every evening'
        assert client.get(path).json()['data']['customer_name'] == 'Manpreet Kaur'
        assert client.get('/api/v1/tickets?q=Manpreet').json()['meta']['total'] >= 1
        assert client.patch(path, json={'status': 'IN_PROGRESS', 'assigned_to_id': users['SUPPORT']}).status_code == 200
        assert client.post(path + '/resolve', json={'resolution': 'Reconnected monitoring gateway'}).status_code == 200
        assert client.patch(path, json={'description': 'Changed after resolution'}).status_code == 409
        assert client.post(path + '/close').status_code == 409
        assert client.post(path + '/confirm').status_code == 200
        assert client.post(path + '/close').status_code == 200
    engine.dispose()
