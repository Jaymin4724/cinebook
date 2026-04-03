from sqlalchemy.ext.asyncio import AsyncSession
from app.models import TheatreModel, TheatreOperatorMapModel


class TheatreRepository:

    def __init__(self, db: AsyncSession):
        self.db = db


    async def create_theatre_repo(
        self,
        name: str,
        area: str,
        city: str
    ) -> TheatreModel:
        
        new_theatre = TheatreModel(
            name=name,
            area=area,
            city=city
        )

        self.db.add(new_theatre)

        await self.db.flush()

        return new_theatre
    
    async def link_operator_to_theatre_repo(
        self,
        theatre_id: int,
        user_id: int
    ) -> TheatreOperatorMapModel:
        
        new_operator = TheatreOperatorMapModel(
            theatre_id=theatre_id,
            user_id=user_id
        )

        self.db.add(new_operator)

        await self.db.flush()

        return new_operator
