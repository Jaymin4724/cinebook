from sqlalchemy.ext.asyncio import AsyncSession
from app.models import TheatreModel, TheatreOperatorMapModel, ShowModel, ScreenModel
from sqlalchemy import select
from datetime import datetime, timezone
from fastapi import HTTPException, status


class TheatreRepository:
    """Handle database operations related to theatres."""

    def __init__(self, db: AsyncSession):

        self.db = db

    async def create_theatre_repo(
        self, name: str, area: str, city: str
    ) -> TheatreModel:
        """Create a new theatre record."""
        new_theatre = TheatreModel(name=name, area=area, city=city)

        self.db.add(new_theatre)

        await self.db.flush()

        return new_theatre

    async def link_operator_to_theatre_repo(
        self, theatre_id: str, user_id: str
    ) -> TheatreOperatorMapModel:
        """Link theatre operator to a theatre."""
        new_operator = TheatreOperatorMapModel(theatre_id=theatre_id, user_id=user_id)

        self.db.add(new_operator)

        await self.db.flush()

        return new_operator

    async def get_theatre_by_id_and_user(
        self, theatre_id: str, user_id: str
    ) -> TheatreOperatorMapModel:
        """Fetch theatre mapping for a user if active."""
        query = (
            select(TheatreOperatorMapModel)
            .join(TheatreModel, TheatreModel.id == TheatreOperatorMapModel.theatre_id)
            .where(
                TheatreOperatorMapModel.user_id == user_id,
                TheatreOperatorMapModel.theatre_id == theatre_id,
                TheatreModel.is_active == True,
            )
        )

        result = await self.db.execute(query)

        return result.scalar_one_or_none()

    async def get_all_theatres_repo(self, page: int, size: int):
        """Fetch paginated list of active theatres."""
        skip = (page - 1) * size
        result = await self.db.scalars(
            select(TheatreModel)
            .where(TheatreModel.is_active == True)
            .offset(skip)
            .limit(size)
        )
        return result.all()

    async def get_all_theatres_by_user_repo(self, user_id: str, page: int, size: int):
        """Fetch paginated list of active theatres for a specific user."""
        skip = (page - 1) * size

        query = (
            select(TheatreModel)
            .join(
                TheatreOperatorMapModel,
                TheatreOperatorMapModel.theatre_id == TheatreModel.id,
            )
            .where(
                TheatreOperatorMapModel.user_id == user_id,
                TheatreModel.is_active == True,
            )
            .offset(skip)
            .limit(size)
        )

        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_theatres_by_movie_repo(
        self, movie_id: str, page: int, size: int
    ) -> list[TheatreModel]:
        """Fetch theatres running a movie with upcoming shows."""
        skip = (page - 1) * size
        query = (
            select(TheatreModel)
            .join(ScreenModel, ScreenModel.theatre_id == TheatreModel.id)
            .join(ShowModel, ShowModel.screen_id == ScreenModel.id)
            .where(
                ShowModel.movie_id == movie_id,
                TheatreModel.is_active == True,
                ShowModel.is_deleted == False,
                ShowModel.start_time > datetime.now(timezone.utc).replace(tzinfo=None),
            )
            .distinct()
            .offset(skip)
            .limit(size)
        )

        result = await self.db.execute(query)
        return result.scalars().all()

    async def delete_theatre_repo(self, theatre_id: str):
        """Soft delete theatre by ID if exists."""
        query = select(TheatreModel).where(
            TheatreModel.is_active == True, TheatreModel.id == theatre_id
        )

        result = await self.db.execute(query)

        theatre_found = result.scalar_one_or_none()

        if not theatre_found:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Theatre not found"
            )

        return await theatre_found.soft_delete(db=self.db)
