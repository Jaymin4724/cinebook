import pytest
import asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool
from sqlalchemy import text
from fakeredis import FakeServer
from fakeredis.aioredis import FakeRedis
from unittest.mock import AsyncMock

from app.main import app
from app.db.base import Base
from app.api.dependencies import get_db, get_redis, get_email_service
from app.core.config import settings

engine = create_async_engine(
    settings.TEST_DB_URL,
    future=True,
    poolclass=NullPool,
)

TestingSessionLocal = async_sessionmaker(
    bind=engine, class_=AsyncSession, expire_on_commit=False
)

shared_server = FakeServer()
global_fake_redis = FakeRedis(server=shared_server, decode_responses=True)


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session", autouse=True)
async def setup_database():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        queries = [
            # 1. Truncate with new tables (bookings included)
            "TRUNCATE TABLE roles, users, permissions, roles_permissions_map, theatres, movies, screens, layouts, bookings, user_details CASCADE;",
            # 2. Insert Roles
            "INSERT INTO roles (role) VALUES ('user'), ('admin'), ('theatre_admin');",
            # 3. Insert All Permissions
            """INSERT INTO permissions (permission) VALUES 
               ('create-user'), ('read-users'), 
               ('create-theatre'), ('read-theatres'), ('delete-theatre'),
               ('create-movie'), ('read-movies'), ('delete-movie'),
               ('create-layout'), 
               ('create-screen'), ('delete-screen'),
               ('create-show'), ('delete-show');""",
            # 4. Map Theatre Admin Permissions
            """INSERT INTO roles_permissions_map (role_id, permission_id)
               SELECT r.id, p.id FROM roles r, permissions p 
               WHERE r.role = 'theatre_admin' 
               AND p.permission IN ('create-layout', 'create-screen', 'delete-screen', 'create-show', 'delete-show');""",
            # 4b. Map Admin Permissions (Gets Everything)
            """INSERT INTO roles_permissions_map (role_id, permission_id)
               SELECT r.id, p.id FROM roles r, permissions p 
               WHERE r.role = 'admin';""",
            # 5. Insert Users
            """INSERT INTO users (email, is_active, role_id) VALUES 
               ('jaymin.dave@armakuni.com', TRUE, (SELECT id FROM roles WHERE role = 'admin' LIMIT 1)),
               ('jaymin4724@gmail.com', TRUE, (SELECT id FROM roles WHERE role = 'theatre_admin' LIMIT 1));""",
            # 6. Insert User Details
            "INSERT INTO user_details (user_id) SELECT id FROM users;",
        ]
        for query in queries:
            await conn.execute(text(query))
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def db():
    async with TestingSessionLocal() as session:
        yield session
        await session.rollback()
        await session.close()


@pytest.fixture
async def client(db):
    mock_email_instance = AsyncMock(spec=get_email_service)
    mock_email_instance.send_otp_email = AsyncMock(return_value=None)

    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_redis] = lambda: global_fake_redis
    app.dependency_overrides[get_email_service] = lambda: mock_email_instance

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
    await global_fake_redis.flushall()
