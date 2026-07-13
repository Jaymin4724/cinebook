import httpx
import pytest
from httpx import ASGITransport

from app.main import app
from app.db.session import get_db
from app.core.redis_config import get_redis
from app.api.dependencies import get_email_service
from app.utils.helper import generate_access_token_and_refresh_token

from tests import factories
from tests.database import (
    test_engine,
    create_test_schema,
    drop_test_schema,
    seed_roles_and_permissions,
    truncate_data_tables,
    override_get_db,
    TestSessionLocal,
)
from tests.fake_redis import create_fake_redis


# --- DATABASE LIFECYCLE ---
@pytest.fixture(scope="session", autouse=True)
async def _setup_database():
    await create_test_schema()
    await seed_roles_and_permissions()
    yield
    await drop_test_schema()
    await test_engine.dispose()


@pytest.fixture(autouse=True)
async def _clean_tables():
    yield
    await truncate_data_tables()


@pytest.fixture
async def db_session():
    async with TestSessionLocal() as session:
        yield session


# --- FAKES ---
@pytest.fixture
def fake_redis():
    return create_fake_redis()


class FakeEmailService:
    """Records sent emails instead of talking to SMTP."""

    def __init__(self):
        self.otp_emails = []
        self.qr_tickets = []

    async def send_otp_email(self, email_to: str, otp: str):
        self.otp_emails.append({"email_to": email_to, "otp": otp})

    async def send_qr_ticket(self, email_to: str, ticket_hash):
        self.qr_tickets.append({"email_to": email_to, "ticket_hash": ticket_hash})


@pytest.fixture
def fake_email_service():
    return FakeEmailService()


@pytest.fixture(autouse=True)
def es_sync_calls(monkeypatch):
    """Capture background Elasticsearch syncs instead of hitting ES."""
    calls = []

    async def _record(instance_data: dict):
        calls.append(instance_data)

    monkeypatch.setattr("app.services.search_sync.async_sync_to_es", _record)
    return calls


# --- APP CLIENT ---
@pytest.fixture
async def client(fake_redis, fake_email_service):
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_redis] = lambda: fake_redis
    app.dependency_overrides[get_email_service] = lambda: fake_email_service

    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c

    app.dependency_overrides.clear()


# --- AUTH HELPERS ---
def make_tokens(user_id) -> dict:
    return generate_access_token_and_refresh_token(
        payload={"user_id": str(user_id)}, response=None
    )


def auth_headers(user_id) -> dict:
    return {"Authorization": f"Bearer {make_tokens(user_id)['access_token']}"}


# --- COMMON PERSONAS ---
@pytest.fixture
async def admin_user(db_session):
    return await factories.create_user(db_session, "admin@test.com", role="admin")


@pytest.fixture
def admin_headers(admin_user):
    return auth_headers(admin_user.id)


@pytest.fixture
async def theatre_admin_user(db_session):
    return await factories.create_user(
        db_session, "operator@test.com", role="theatre_admin"
    )


@pytest.fixture
def theatre_admin_headers(theatre_admin_user):
    return auth_headers(theatre_admin_user.id)


@pytest.fixture
async def regular_user(db_session):
    return await factories.create_user(db_session, "user@test.com", role="user")


@pytest.fixture
def user_headers(regular_user):
    return auth_headers(regular_user.id)


@pytest.fixture
async def bookable_show(db_session, theatre_admin_user):
    """Theatre -> layout -> screen -> movie -> show, owned by theatre_admin_user."""
    return await factories.create_bookable_show(db_session, operator=theatre_admin_user)
