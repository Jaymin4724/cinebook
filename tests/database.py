import pytest
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
from sqlalchemy import text

from app.db.base import Base
from app.core.config import settings


engine = create_async_engine(
    settings.TEST_DB_URL,
    future=True,
    poolclass=NullPool,
)

AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

SEED_QUERIES = [
    "TRUNCATE TABLE roles, users, permissions, roles_permissions_map, theatres, movies, screens, layouts, bookings, user_details CASCADE;",
    "INSERT INTO roles (role) VALUES ('user'), ('admin'), ('theatre_admin');",
    """INSERT INTO permissions (permission) VALUES
       ('create-user'), ('read-users'),
       ('create-theatre'), ('read-theatres'), ('delete-theatre'),
       ('create-movie'), ('read-movies'), ('delete-movie'),
       ('create-layout'),
       ('create-screen'), ('delete-screen'),
       ('create-show'), ('delete-show');""",
    """INSERT INTO roles_permissions_map (role_id, permission_id)
       SELECT r.id, p.id FROM roles r, permissions p
       WHERE r.role = 'theatre_admin'
       AND p.permission IN ('create-layout', 'create-screen', 'delete-screen', 'create-show', 'delete-show');""",
    """INSERT INTO roles_permissions_map (role_id, permission_id)
       SELECT r.id, p.id FROM roles r, permissions p
       WHERE r.role = 'admin';""",
    """INSERT INTO users (email, is_active, role_id) VALUES
       ('jaymin.dave@armakuni.com', TRUE, (SELECT id FROM roles WHERE role = 'admin' LIMIT 1)),
       ('jaymin4724@gmail.com', TRUE, (SELECT id FROM roles WHERE role = 'theatre_admin' LIMIT 1));""",
    "INSERT INTO user_details (user_id) SELECT id FROM users;",
]


@pytest.fixture(scope="session", autouse=True)
async def setup_database():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        for query in SEED_QUERIES:
            await conn.execute(text(query))
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def db():
    async with engine.connect() as conn:
        trans = await conn.begin()
        session = AsyncSession(bind=conn, expire_on_commit=False)
        try:
            yield session
        finally:
            await session.close()
            await trans.rollback()