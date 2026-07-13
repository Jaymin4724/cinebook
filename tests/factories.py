"""Direct-to-DB data factories for tests.

Each factory commits, so the data is visible to the request-scoped
sessions the app opens per API call.
"""

import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    RoleModel,
    UserModel,
    UserDetailModel,
    TheatreModel,
    TheatreOperatorMapModel,
    LayoutModel,
    ScreenModel,
    MovieModel,
    ShowModel,
    BookingModel,
    BookedSeatMapModel,
)
from app.utils.polish_seat_layout import polish_seat_layout


def raw_layout_grid() -> dict:
    """A 2x3 grid: row A = gold seats with an aisle gap, row B = standard.

    Polishes into seats A1 [0,0], A2 [0,2], B1-B3 (5 seats total).
    The gap is an explicit "aisle" cell rather than None because
    SeatLayoutService.generate_base_layout crashes on None cells.
    """
    return {
        "layout": [
            [
                {"grid_type": "seat", "category": "gold"},
                {"grid_type": "aisle"},
                {"grid_type": "seat", "category": "gold"},
            ],
            [
                {"grid_type": "seat", "category": "standard"},
                {"grid_type": "seat", "category": "standard"},
                {"grid_type": "seat", "category": "standard"},
            ],
        ],
        "metadata": {"grid_rows": 2, "grid_columns": 3},
    }


CATEGORY_PRICING = {"gold": 300.0, "standard": 150.0}


async def create_user(
    db: AsyncSession, email: str, role: str = "user", is_active: bool = True
) -> UserModel:
    role_id = (
        await db.execute(select(RoleModel.id).where(RoleModel.role == role))
    ).scalar_one()

    user = UserModel(email=email, role_id=role_id, is_active=is_active)
    db.add(user)
    await db.flush()

    db.add(UserDetailModel(user_id=user.id))
    await db.commit()
    return user


async def create_theatre(
    db: AsyncSession,
    operator: UserModel | None = None,
    name: str = "pvr cinemas",
    area: str = "satellite",
    city: str = "ahmedabad",
    is_active: bool = True,
) -> TheatreModel:
    theatre = TheatreModel(name=name, area=area, city=city, is_active=is_active)
    db.add(theatre)
    await db.flush()

    if operator is not None:
        db.add(TheatreOperatorMapModel(theatre_id=theatre.id, user_id=operator.id))

    await db.commit()
    return theatre


async def create_layout(
    db: AsyncSession,
    theatre: TheatreModel,
    name: str = "standard layout",
    raw_grid: dict | None = None,
) -> LayoutModel:
    layout = LayoutModel(
        name=name,
        layout=polish_seat_layout(raw_grid or raw_layout_grid()),
        theatre_id=theatre.id,
    )
    db.add(layout)
    await db.commit()
    return layout


async def create_screen(
    db: AsyncSession,
    theatre: TheatreModel,
    layout: LayoutModel,
    name: str = "screen 1",
    is_active: bool = True,
) -> ScreenModel:
    screen = ScreenModel(
        name=name, theatre_id=theatre.id, layout_id=layout.id, is_active=is_active
    )
    db.add(screen)
    await db.commit()
    return screen


async def create_movie(
    db: AsyncSession,
    name: str = "inception",
    duration_minutes: int = 120,
    imdb_id: str | None = None,
    is_deleted: bool = False,
) -> MovieModel:
    movie = MovieModel(
        name=name,
        duration=timedelta(minutes=duration_minutes),
        description="a test movie",
        rating=8.5,
        genre="sci-fi",
        imdb_id=imdb_id or f"tt{uuid.uuid4().hex[:8]}",
        is_deleted=is_deleted,
    )
    db.add(movie)
    await db.commit()
    return movie


async def create_show(
    db: AsyncSession,
    screen: ScreenModel,
    movie: MovieModel,
    start_time: datetime | None = None,
    category_pricing: dict | None = None,
    is_deleted: bool = False,
) -> ShowModel:
    if start_time is None:
        start_time = datetime.now(timezone.utc) + timedelta(days=1)

    show = ShowModel(
        start_time=start_time.replace(tzinfo=None),
        screen_id=screen.id,
        movie_id=movie.id,
        category_pricing=category_pricing or dict(CATEGORY_PRICING),
        is_deleted=is_deleted,
    )
    db.add(show)
    await db.commit()
    return show


async def create_booking(
    db: AsyncSession,
    user: UserModel,
    show: ShowModel,
    seats: list[str],
    total_bill: float = 0.0,
    is_cancelled: bool = False,
) -> BookingModel:
    booking = BookingModel(
        user_id=user.id,
        show_id=show.id,
        number_of_seats=len(seats),
        total_bill=total_bill,
        is_cancelled=is_cancelled,
    )
    db.add(booking)
    await db.flush()

    db.add_all(
        BookedSeatMapModel(
            seats_number=seat,
            booking_id=booking.id,
            show_id=show.id,
            is_cancelled=is_cancelled,
        )
        for seat in seats
    )
    await db.commit()
    return booking


async def create_bookable_show(
    db: AsyncSession,
    operator: UserModel,
    start_time: datetime | None = None,
) -> SimpleNamespace:
    """Build the whole chain theatre -> layout -> screen -> movie -> show."""
    theatre = await create_theatre(db, operator=operator)
    layout = await create_layout(db, theatre)
    screen = await create_screen(db, theatre, layout)
    movie = await create_movie(db)
    show = await create_show(db, screen, movie, start_time=start_time)

    return SimpleNamespace(
        theatre=theatre, layout=layout, screen=screen, movie=movie, show=show
    )
