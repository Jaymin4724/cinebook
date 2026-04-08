from sqlalchemy.ext.asyncio import AsyncSession
from app.models import ShowModel, MovieModel
from sqlalchemy import select, desc
from datetime import datetime, timezone
from sqlalchemy.orm import selectinload


class ShowRepository:

    def __init__(
        self,
        db: AsyncSession
    ):

        self.db = db


    async def get_show_last_show_less_than_time(
        self,
        show_time: datetime,
        screen_id: str
    ):
        
        query = (
            select(ShowModel)
            .options(selectinload(ShowModel.movie))
            .where(
                ShowModel.start_time < show_time.replace(tzinfo=None),
                ShowModel.screen_id == screen_id,
                ShowModel.is_deleted == False
            )
            .order_by(desc(ShowModel.start_time))
            .limit(1)
        )

        result = await self.db.execute(query)

        return result.scalar_one_or_none()
    

    async def get_show_in_between_time(
        self,
        start_time: datetime,
        end_time: datetime,
        screen_id: str
    ):
        
        query = select(
            ShowModel
        ).where(
            ShowModel.start_time > start_time.replace(tzinfo=None),
            ShowModel.start_time < end_time.replace(tzinfo=None),
            ShowModel.screen_id == screen_id,
            ShowModel.is_deleted == False
        )

        result = await self.db.execute(query)

        return result.scalar_one_or_none()
    

    async def create_show_repo(
        self,
        start_time: datetime,
        screen_id: str,
        movie_id: str,
        category_pricing: dict
    ):
        
        new_show = ShowModel(
            start_time=start_time.replace(tzinfo=None),
            screen_id=screen_id,
            movie_id=movie_id,
            category_pricing=category_pricing
        )

        self.db.add(new_show)

        await self.db.flush()

        return new_show