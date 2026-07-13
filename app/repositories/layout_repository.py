from sqlalchemy.ext.asyncio import AsyncSession
from app.models import LayoutModel, TheatreModel, TheatreOperatorMapModel
from sqlalchemy import select
from fastapi import HTTPException, status


class LayoutRepository:
    """Handle database operations related to layouts."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_layout_repository(self, name: str, layout: dict, theatre_id: str):
        """Create a new layout for a theatre."""
        new_layout = LayoutModel(name=name, layout=layout, theatre_id=theatre_id)

        self.db.add(new_layout)

        await self.db.flush()

        return new_layout

    async def get_layout_by_id_and_theatre(self, theatre_id: str, layout_id: str):
        """Fetch layout by ID and theatre."""
        query = select(LayoutModel).where(
            LayoutModel.id == layout_id, LayoutModel.theatre_id == theatre_id
        )

        result = await self.db.execute(query)

        return result.scalar_one_or_none()

    async def get_layout_by_id_and_user(self, layout_id: str, user_id: str):
        """Fetch a layout if it belongs to a theatre owned by the user."""
        query = (
            select(LayoutModel)
            .join(TheatreModel, LayoutModel.theatre_id == TheatreModel.id)
            .join(
                TheatreOperatorMapModel,
                TheatreOperatorMapModel.theatre_id == TheatreModel.id,
            )
            .where(
                LayoutModel.id == layout_id,
                TheatreOperatorMapModel.user_id == user_id,
                TheatreModel.is_active == True,
            )
        )

        result = await self.db.execute(query)

        return result.scalar_one_or_none()

    async def update_layout_repo(
        self, layout_id: str, user_id: str, update_data: dict
    ) -> LayoutModel:
        """Partially update a layout's editable fields (name only)."""
        layout_found = await self.get_layout_by_id_and_user(
            layout_id=layout_id, user_id=user_id
        )

        if not layout_found:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Layout not found"
            )

        for field, value in update_data.items():
            setattr(layout_found, field, value)

        self.db.add(layout_found)
        return layout_found
