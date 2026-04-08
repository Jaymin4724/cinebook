from sqlalchemy.ext.asyncio import AsyncSession
from app.models import TheatreModel, TheatreOperatorMapModel, ShowModel, ScreenModel
from sqlalchemy import select
from datetime import datetime
from datetime import datetime, timezone


class TheatreRepository:

    def __init__(self, db: AsyncSession):

        self.db = db

    async def create_theatre_repo(
        self, name: str, area: str, city: str
    ) -> TheatreModel:

        new_theatre = TheatreModel(name=name, area=area, city=city)

        self.db.add(new_theatre)

        await self.db.flush()

        return new_theatre

    async def link_operator_to_theatre_repo(
        self, theatre_id: str, user_id: str
    ) -> TheatreOperatorMapModel:

        new_operator = TheatreOperatorMapModel(theatre_id=theatre_id, user_id=user_id)

        self.db.add(new_operator)

        await self.db.flush()

        return new_operator

    async def get_theatre_by_id_and_user(
        self, theatre_id: str, user_id: str
    ) -> TheatreOperatorMapModel:

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

        skip = (page - 1) * size
        result = await self.db.scalars(
            select(TheatreModel)
            .where(TheatreModel.is_active == True)
            .offset(skip)
            .limit(size)
        )
        return result.all()

    async def get_theatres_by_movie_repo(
        self, movie_id: str, page: int, size: int
    ) -> list[TheatreModel]:
        skip = (page - 1) * size
        query = (
            select(TheatreModel)
            .join(ScreenModel, ScreenModel.theatre_id == TheatreModel.id)
            .join(ShowModel, ShowModel.screen_id == ScreenModel.id)
            .where(
                ShowModel.movie_id == movie_id,
                TheatreModel.is_active == True,
                ShowModel.is_deleted == False,
                ShowModel.start_time > datetime.now(timezone.utc),
            )
            .distinct()
            .offset(skip)
            .limit(size)
        )

        result = await self.db.execute(query)
        return result.scalars().all()
