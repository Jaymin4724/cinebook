from sqlalchemy.ext.asyncio import AsyncSession
from app.models import ScreenModel


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
