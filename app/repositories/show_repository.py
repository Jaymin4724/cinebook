from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from app.models import ShowModel, ScreenModel, TheatreModel, TheatreOperatorMapModel, MovieModel
from sqlalchemy import select, desc
from datetime import datetime, timedelta
from sqlalchemy.orm import selectinload, joinedload
from app.services.seat_layout_service import SeatLayoutService
from fastapi import HTTPException, status
from uuid import UUID


class ShowRepository:
    """Handle database operations related to shows."""

    def __init__(self, db: AsyncSession):

        self.db = db

    async def get_show_last_show_less_than_time(
        self, show_time: datetime, screen_id: str
    ):
        """Fetch latest show before given time for a screen."""
        query = (
            select(ShowModel)
            .options(selectinload(ShowModel.movie))
            .where(
                ShowModel.start_time < show_time.replace(tzinfo=None),
                ShowModel.screen_id == screen_id,
                ShowModel.is_deleted == False,
            )
            .order_by(desc(ShowModel.start_time))
            .limit(1)
        )

        result = await self.db.execute(query)

        return result.scalar_one_or_none()

    async def get_show_in_between_time(
        self, start_time: datetime, end_time: datetime, screen_id: str
    ):
        """Check if any show exists in given time range."""
        query = (
            select(ShowModel)
            .where(
                ShowModel.start_time >= start_time.replace(tzinfo=None),
                ShowModel.start_time <= end_time.replace(tzinfo=None),
                ShowModel.screen_id == screen_id,
                ShowModel.is_deleted == False,
            )
            .limit(1)
        )

        result = await self.db.execute(query)

        return result.scalar_one_or_none()

    async def create_show_repo(
        self,
        start_time: datetime,
        screen_id: str,
        movie_id: str,
        category_pricing: dict,
    ):
        """Create a new show record."""
        new_show = ShowModel(
            start_time=start_time.replace(tzinfo=None),
            screen_id=screen_id,
            movie_id=movie_id,
            category_pricing=category_pricing,
        )

        self.db.add(new_show)

        await self.db.flush()

        return new_show

    async def get_shows_repo(
        self, theatre_id: UUID, movie_id: str, page: int = 1, size: int = 10
    ):
        """Fetch shows for a movie in a theatre with pagination."""
        offset = (page - 1) * size

        query = (
            select(ShowModel)
            .join(ScreenModel, ShowModel.screen_id == ScreenModel.id)
            .where(
                ShowModel.movie_id == movie_id,
                ScreenModel.theatre_id == theatre_id,
                ShowModel.is_deleted == False,
            )
            .options(
                joinedload(ShowModel.movie),
                joinedload(ShowModel.screen).joinedload(ScreenModel.theatre),
            )
            .order_by(ShowModel.start_time)
            .offset(offset)
            .limit(size)
        )

        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_show_by_id_repo(
        self, show_id: str, seat_layout_service: SeatLayoutService
    ) -> ShowModel:
        """Fetch show layout by show ID."""
        return await seat_layout_service.generate_show_layout(show_id)

    async def delete_show_repo(self, show_id: str, user_id: str):
        """Soft delete show if it belongs to user."""
        query = (
            select(ShowModel)
            .join(ScreenModel, ShowModel.screen_id == ScreenModel.id)
            .join(TheatreModel, ScreenModel.theatre_id == TheatreModel.id)
            .join(
                TheatreOperatorMapModel,
                TheatreModel.id == TheatreOperatorMapModel.theatre_id,
            )
            .where(
                ShowModel.id == show_id,
                ShowModel.is_deleted == False,
                TheatreOperatorMapModel.user_id == user_id,
            )
        )

        result = await self.db.execute(query)

        show_found = result.scalar_one_or_none()

        if not show_found:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Show not found"
            )

        return await show_found.soft_delete(db=self.db)

    async def get_show_end_time(self, show_id: str):

        query = select(
            ShowModel.start_time,
            MovieModel.duration
        ).join(
            MovieModel, ShowModel.movie_id == MovieModel.id
        ).where(
            ShowModel.id == show_id
        )

        result = await self.db.execute(query)

        show_found = result.first()

        if not show_found:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Show not found"
            )

        show_start_time = show_found.start_time
        movie_duration_seconds = show_found.duration.total_seconds()

        return show_start_time + timedelta(seconds=movie_duration_seconds)

