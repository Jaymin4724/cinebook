from datetime import datetime, timedelta, timezone
from fastapi import HTTPException, status
from app.core.redis_config import Redis

from app.repositories.screen_repository import ScreenRepository
from app.repositories.movie_repository import MovieRepository
from app.repositories.show_repository import ShowRepository


async def validate_start_time_of_show(show_datetime: datetime):
    """Validate show timing within allowed time range."""
    now = datetime.now(timezone.utc)

    if show_datetime > (now + timedelta(days=3)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Show date cannot be more than 3 days in the future.",
        )

    if show_datetime < (now + timedelta(hours=2)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Show must be scheduled at least 2 hours from now.",
        )

    return show_datetime


async def validate_category_price(
    category_price: dict, screen_id: str, screen_repo: ScreenRepository
):
    """Validate category pricing against screen layout."""
    screen_layout = await screen_repo.get_layout_by_screen_repo(screen_id=screen_id)

    seat_category_list = screen_layout.layout.get("category")

    for category in seat_category_list:
        if category not in category_price:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Category not found in price list",
            )

        try:
            float(category_price[category])
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid price input"
            )


async def validate_movie_and_return_time(movie_id: str, movie_repo: MovieRepository):
    """Validate movie exists and return its duration."""
    movie_found = await movie_repo.get_movie_by_id(movie_id=movie_id)

    if not movie_found:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Movie not found"
        )

    return movie_found.duration.total_seconds()


async def validate_show_overlap(
    start_time: datetime,
    movie_duration: timedelta,
    screen_id: str,
    show_repo: ShowRepository,
):
    """Validate show does not overlap with existing shows."""
    show_start_time = start_time
    show_end_time = start_time + movie_duration

    previous_show = await show_repo.get_show_last_show_less_than_time(
        show_time=start_time, screen_id=screen_id
    )

    if previous_show:
        previos_show_end_time = previous_show.start_time.replace(
            tzinfo=timezone.utc
        ) + timedelta(seconds=previous_show.movie.duration.total_seconds())

        if previos_show_end_time > show_start_time:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Show is overlapping with previous show",
            )

    show_in_between = await show_repo.get_show_in_between_time(
        start_time=show_start_time, end_time=show_end_time, screen_id=screen_id
    )

    if show_in_between:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Show is overlapping with next movie",
        )
