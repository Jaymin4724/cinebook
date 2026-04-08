from sqlalchemy.ext.asyncio import AsyncSession
from app.models import ScreenModel, LayoutModel, TheatreModel, TheatreOperatorMapModel
from sqlalchemy import select


class ScreenRepository:

    def __init__(
        self, 
        db: AsyncSession
    ):
        self.db = db

    
    async def create_screen_repository(
        self,
        name: str, 
        layout_id: str,
        theatre_id: str
    ):
        
        new_screen = ScreenModel(
            name=name,
            layout_id=layout_id,
            theatre_id=theatre_id
        )

        self.db.add(new_screen)

        await self.db.flush()

        return new_screen


    async def get_layout_by_screen_repo(
        self,
        screen_id: str
    ):
        
        query = select(
            LayoutModel
        ).join(
            ScreenModel, ScreenModel.layout_id == LayoutModel.id
        ).where(
            ScreenModel.id == screen_id,
            ScreenModel.is_active == True
        )

        result = await self.db.execute(query)

        return result.scalar_one_or_none()
    

    async def validate_screen_and_user(
        self,
        screen_id: str,
        user_id: str
    ):
        query = select(
            ScreenModel
        ).join(
            TheatreModel, ScreenModel.theatre_id == TheatreModel.id
        ).join(
            TheatreOperatorMapModel, TheatreOperatorMapModel.theatre_id == TheatreModel.id
        ).where(
            ScreenModel.id == screen_id,
            ScreenModel.is_active == True,
            TheatreModel.is_active == True,
            TheatreOperatorMapModel.user_id == user_id
        )

        result = await self.db.execute(query)

        return result.scalar_one_or_none()