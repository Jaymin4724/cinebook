from sqlalchemy.ext.asyncio import AsyncSession
from app.models import LayoutModel
from sqlalchemy import select


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
        theatre_id: str
    ):
        
        new_layout = LayoutModel(
            name=name,
            layout=layout,
            theatre_id=theatre_id
        )

        self.db.add(new_layout)

        await self.db.flush()

        return new_layout
    
    async def get_layout_by_id_and_theatre(
        self,
        theatre_id: str,
        layout_id: str
    ):
        
        query = select(
            LayoutModel
        ).where(
            LayoutModel.id == layout_id,
            LayoutModel.theatre_id == theatre_id
        )

        result = await self.db.execute(query)

        return result.scalar_one_or_none()
