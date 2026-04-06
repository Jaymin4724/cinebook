from sqlalchemy.ext.asyncio import AsyncSession
from app.models import LayoutModel


class LayoutRepository:

    def __init__(
        self, 
        db: AsyncSession
    ):
        self.db = db

    
    async def create_layout_repository(
        self,
        name: str, 
        layout: dict, 
        theatre_id: int
    ):
        
        new_layout = LayoutModel(
            name=name,
            layout=layout,
            theatre_id=theatre_id
        )

        self.db.add(new_layout)

        await self.db.flush()

        return new_layout
