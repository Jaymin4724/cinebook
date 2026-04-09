from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from app.models import ShowModel, ScreenModel
from sqlalchemy import select, desc
from datetime import datetime
from sqlalchemy.orm import selectinload, joinedload
from app.utils.generate_layout import RedisSeatLayoutManagement


class ShowRepository:

    def __init__(self, db: AsyncSession):

        self.db = db

    async def get_show_last_show_less_than_time(
        self, show_time: datetime, screen_id: str
    ):

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

        query = select(ShowModel).where(
            ShowModel.start_time > start_time.replace(tzinfo=None),
            ShowModel.start_time < end_time.replace(tzinfo=None),
            ShowModel.screen_id == screen_id,
            ShowModel.is_deleted == False,
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
        self, theatre_id: str, movie_id: str, page: int = 1, size: int = 10
    ):
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

    async def get_show_by_id_repo(self, show_id: str, redis) -> ShowModel:
        # # Chain: Show -> Movie AND Show -> Screen -> Theatre
        # query = (
        #     select(ShowModel)
        #     .options(
        #         joinedload(ShowModel.movie),
        #         joinedload(ShowModel.screen).joinedload(ScreenModel.theatre),
        #     )
        #     .where(ShowModel.id == show_id)
        # )
        # result = await self.db.execute(query)
        # return result.scalar_one_or_none()
        LayoutManagementObj = RedisSeatLayoutManagement(self.db, redis, show_id=show_id)
        return await LayoutManagementObj.generate_show_layout()
