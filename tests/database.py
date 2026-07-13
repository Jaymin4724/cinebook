from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker,
)
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.db.base import Base
import app.models  # noqa: F401  (register all models on Base.metadata)

test_engine = create_async_engine(settings.TEST_DB_URL, poolclass=NullPool)

TestSessionLocal = async_sessionmaker(
    bind=test_engine, class_=AsyncSession, expire_on_commit=False, autoflush=False
)


async def override_get_db():
    """Test replacement for app.db.session.get_db."""
    async with TestSessionLocal() as db:
        try:
            yield db
        finally:
            await db.close()


# The partial unique index lives only in the alembic migration
# (d719f771d6d4), not in the model metadata, so create_all alone
# would silently skip the double-booking backstop the tests rely on.
PARTIAL_UNIQUE_INDEX_SQL = """
CREATE UNIQUE INDEX IF NOT EXISTS uq_booked_seats_map_show_seat_active
ON booked_seats_map (show_id, seats_number)
WHERE is_cancelled = false
"""

# Mirrors seed_db.sql
ALL_PERMISSIONS = [
    "create-user", "read-users",
    "create-theatre", "read-theatres", "delete-theatre", "update-theatre",
    "create-movie", "read-movies", "delete-movie", "update-movie",
    "create-layout", "update-layout",
    "create-screen", "read-my-theatres", "read-my-screens",
    "delete-screen", "update-screen",
    "create-show", "delete-show", "update-show",
    "verify-ticket",
]

THEATRE_ADMIN_PERMISSIONS = [
    "create-layout", "update-layout",
    "create-screen", "read-my-theatres", "read-my-screens",
    "delete-screen", "update-screen",
    "create-show", "delete-show", "update-show",
    "verify-ticket",
]

# Regular users hold no admin-panel permissions: public browsing and
# booking routes only require authentication, not permissions.
USER_PERMISSIONS = []

# Truncated between tests; roles/permissions seed data is kept.
DATA_TABLES = [
    "booked_tickets",
    "booked_seats_map",
    "bookings",
    "shows",
    "screens",
    "layouts",
    "theatre_operators_map",
    "movies",
    "theatres",
    "user_details",
    "users",
]


async def create_test_schema():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.execute(text(PARTIAL_UNIQUE_INDEX_SQL))


async def drop_test_schema():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


async def seed_roles_and_permissions():
    """Seed roles, permissions and their mappings, mirroring seed_db.sql."""
    from app.models import RoleModel, PermissionModel, RolePermissionMap

    async with TestSessionLocal() as db:
        async with db.begin():
            roles = {
                name: RoleModel(role=name)
                for name in ("user", "admin", "theatre_admin")
            }
            permissions = {
                name: PermissionModel(permission=name) for name in ALL_PERMISSIONS
            }
            db.add_all(roles.values())
            db.add_all(permissions.values())
            await db.flush()

            mappings = {
                "admin": ALL_PERMISSIONS,
                "theatre_admin": THEATRE_ADMIN_PERMISSIONS,
                "user": USER_PERMISSIONS,
            }
            for role_name, permission_names in mappings.items():
                db.add_all(
                    RolePermissionMap(
                        role_id=roles[role_name].id,
                        permission_id=permissions[name].id,
                    )
                    for name in permission_names
                )


async def truncate_data_tables():
    async with test_engine.begin() as conn:
        await conn.execute(text(f"TRUNCATE {', '.join(DATA_TABLES)} CASCADE"))
