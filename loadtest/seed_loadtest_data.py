"""Seed a fresh, bookable show into the test database for load testing.

This talks to Postgres directly (via ``TEST_DB_URL``) the same way the test
factories do — it does NOT go through the API. Each run creates a brand new
theatre -> layout -> screen -> movie -> show plus a pool of regular users, so
every run starts with an empty seat map. It then writes everything Locust
needs (show id, seat ids, user ids) to ``loadtest/loadtest_data.json``.

Run it against the SAME database your running app is pointed at (see the
README — the app must use the test DB so it can see this data).

    uv run python loadtest/seed_loadtest_data.py

Configurable via environment variables:
    LOADTEST_USERS   number of regular users to create    (default 50)
    LOADTEST_ROWS    seat-grid rows                       (default 20)
    LOADTEST_COLS    seat-grid columns                    (default 30)
"""

import os
import sys
import json
import uuid
import asyncio
from pathlib import Path
from datetime import datetime, timedelta, timezone

# Make the project root importable when this file is run as a plain script
# (python loadtest/seed_loadtest_data.py). Without this, `import app` fails
# because sys.path[0] would be the loadtest/ directory.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy import text, select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.db.base import Base
import app.models  # noqa: F401  (registers all tables on Base.metadata)
from app.models import (
    RoleModel,
    PermissionModel,
    RolePermissionMap,
    UserModel,
    UserDetailModel,
    TheatreModel,
    TheatreOperatorMapModel,
    LayoutModel,
    ScreenModel,
    MovieModel,
    ShowModel,
)
from app.utils.polish_seat_layout import polish_seat_layout

# --- Tunables -------------------------------------------------------------
NUM_USERS = int(os.getenv("LOADTEST_USERS", "50"))
GRID_ROWS = int(os.getenv("LOADTEST_ROWS", "20"))
GRID_COLS = int(os.getenv("LOADTEST_COLS", "30"))

# Two seat categories so pricing resolution is exercised. Every category that
# appears in the grid MUST have an entry here (the layout service prices seats
# by looking the category up in the show's category_pricing).
CATEGORY_PRICING = {"gold": 300.0, "standard": 150.0}

OUTPUT_FILE = PROJECT_ROOT / "loadtest" / "loadtest_data.json"

# Roles/permissions to guarantee exist. Regular users need no permissions
# (booking routes only require authentication), but create_user looks up the
# "user" role by name, so the roles must be present.
ROLES = ("user", "admin", "theatre_admin")

# Kept in sync with app/scripts/seed_db.py + tests/database.py
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

PARTIAL_UNIQUE_INDEX_SQL = """
CREATE UNIQUE INDEX IF NOT EXISTS uq_booked_seats_map_show_seat_active
ON booked_seats_map (show_id, seats_number)
WHERE is_cancelled = false
"""


def build_raw_grid(rows: int, cols: int) -> dict:
    """Build a raw (unpolished) seat grid: first 2 rows gold, the rest standard."""
    grid = []
    for r in range(rows):
        category = "gold" if r < 2 else "standard"
        grid.append(
            [{"grid_type": "seat", "category": category} for _ in range(cols)]
        )
    return {"layout": grid, "metadata": {"grid_rows": rows, "grid_columns": cols}}


async def ensure_schema(engine) -> None:
    """Create tables + the double-booking guard index if they don't exist."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.execute(text(PARTIAL_UNIQUE_INDEX_SQL))


async def ensure_roles_and_permissions(session: AsyncSession) -> None:
    """Idempotently seed roles, permissions and admin<->permission mappings."""
    existing_roles = set(
        (await session.execute(select(RoleModel.role))).scalars().all()
    )
    if not existing_roles:
        session.add_all(RoleModel(role=name) for name in ROLES)

    existing_perms = set(
        (await session.execute(select(PermissionModel.permission))).scalars().all()
    )
    missing_perms = [p for p in ALL_PERMISSIONS if p not in existing_perms]
    session.add_all(PermissionModel(permission=p) for p in missing_perms)

    await session.flush()

    # Give the admin role every permission (only if it has none yet).
    admin_role = (
        await session.execute(select(RoleModel).where(RoleModel.role == "admin"))
    ).scalar_one()
    has_mapping = (
        await session.execute(
            select(RolePermissionMap.id).where(
                RolePermissionMap.role_id == admin_role.id
            )
        )
    ).first()
    if not has_mapping:
        all_perms = (await session.execute(select(PermissionModel))).scalars().all()
        session.add_all(
            RolePermissionMap(role_id=admin_role.id, permission_id=p.id)
            for p in all_perms
        )


async def create_bookable_show(session: AsyncSession) -> dict:
    """Create theatre -> layout -> screen -> movie -> show. Return their ids + seats."""
    user_role_id = (
        await session.execute(select(RoleModel.id).where(RoleModel.role == "theatre_admin"))
    ).scalar_one()

    operator = UserModel(email=f"loadtest-operator-{uuid.uuid4().hex[:8]}@test.com", role_id=user_role_id)
    session.add(operator)
    await session.flush()
    session.add(UserDetailModel(user_id=operator.id))

    theatre = TheatreModel(name="loadtest cinema", area="loadzone", city="loadcity")
    session.add(theatre)
    await session.flush()
    session.add(TheatreOperatorMapModel(theatre_id=theatre.id, user_id=operator.id))

    polished = polish_seat_layout(build_raw_grid(GRID_ROWS, GRID_COLS))
    layout = LayoutModel(name="loadtest layout", layout=polished, theatre_id=theatre.id)
    session.add(layout)
    await session.flush()

    screen = ScreenModel(name="screen 1", theatre_id=theatre.id, layout_id=layout.id)
    session.add(screen)
    await session.flush()

    movie = MovieModel(
        name="loadtest movie",
        duration=timedelta(minutes=120),
        description="a movie used only for load testing",
        rating=8.0,
        genre="action",
        imdb_id=f"tt{uuid.uuid4().hex[:8]}",
    )
    session.add(movie)
    await session.flush()

    show = ShowModel(
        start_time=(datetime.now(timezone.utc) + timedelta(days=2)).replace(tzinfo=None),
        screen_id=screen.id,
        movie_id=movie.id,
        category_pricing=dict(CATEGORY_PRICING),
    )
    session.add(show)
    await session.flush()

    seat_ids = list(polished["seat_mapping"].keys())
    return {
        "show_id": str(show.id),
        "theatre_id": str(theatre.id),
        "movie_id": str(movie.id),
        "movie_name": movie.name,
        "seat_ids": seat_ids,
    }


async def create_users(session: AsyncSession, count: int) -> list[str]:
    """Create `count` regular users and return their ids."""
    user_role_id = (
        await session.execute(select(RoleModel.id).where(RoleModel.role == "user"))
    ).scalar_one()

    users = []
    for _ in range(count):
        user = UserModel(email=f"loadtest-user-{uuid.uuid4().hex[:10]}@test.com", role_id=user_role_id)
        session.add(user)
        users.append(user)
    await session.flush()

    session.add_all(UserDetailModel(user_id=u.id) for u in users)
    return [str(u.id) for u in users]


async def main() -> None:
    print(f"Seeding load-test data into TEST_DB_URL ({_safe_url(settings.TEST_DB_URL)})")
    engine = create_async_engine(settings.TEST_DB_URL, poolclass=NullPool)

    await ensure_schema(engine)

    session_local = async_sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False, autoflush=False
    )
    async with session_local() as session:
        async with session.begin():
            await ensure_roles_and_permissions(session)
            show = await create_bookable_show(session)
            user_ids = await create_users(session, NUM_USERS)

    await engine.dispose()

    payload = {
        "host": os.getenv("LOADTEST_HOST", "http://localhost:8000"),
        "show_id": show["show_id"],
        "theatre_id": show["theatre_id"],
        "movie_id": show["movie_id"],
        "movie_name": show["movie_name"],
        "seat_ids": show["seat_ids"],
        "user_ids": user_ids,
        "grid": {"rows": GRID_ROWS, "cols": GRID_COLS, "total_seats": len(show["seat_ids"])},
    }
    OUTPUT_FILE.write_text(json.dumps(payload, indent=2))

    print(f"  users created : {len(user_ids)}")
    print(f"  show id       : {show['show_id']}")
    print(f"  theatre id    : {show['theatre_id']}")
    print(f"  movie id      : {show['movie_id']}")
    print(f"  seats         : {len(show['seat_ids'])} ({GRID_ROWS}x{GRID_COLS} grid)")
    print(f"  written to    : {OUTPUT_FILE}")


def _safe_url(url: str) -> str:
    """Hide credentials when echoing the DB URL to the console."""
    if "@" in url:
        return url.split("@", 1)[0].rsplit(":", 1)[0] + ":***@" + url.split("@", 1)[1]
    return url


if __name__ == "__main__":
    asyncio.run(main())
