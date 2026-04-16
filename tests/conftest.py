import pytest
import asyncio
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock

from app.main import app
from app.api.dependencies import get_db, get_redis, get_email_service

from tests.fake_redis import global_fake_redis
from tests.database import (
    setup_database,
    db,
)


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def client(db):
    mock_email_instance = AsyncMock()
    mock_email_instance.send_otp_email = AsyncMock(return_value=None)

    async def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_redis] = lambda: global_fake_redis
    app.dependency_overrides[get_email_service] = lambda: mock_email_instance

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
    await global_fake_redis.flushall()
