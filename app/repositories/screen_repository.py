from sqlalchemy.ext.asyncio import AsyncSession
from app.models import ScreenModel, LayoutModel, TheatreModel, TheatreOperatorMapModel
from sqlalchemy import select
from fastapi import HTTPException, status


class ScreenRepository:
    """Handle database operations related to screens."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_screen_repo(self, name: str, layout_id: str, theatre_id: str):
        """Create a new screen for a theatre."""
        new_screen = ScreenModel(name=name, layout_id=layout_id, theatre_id=theatre_id)

        self.db.add(new_screen)

        await self.db.flush()

        return new_screen

    async def get_all_screens_by_user_repo(self, user_id: str, page: int, size: int):
        """Fetch paginated list of screens with theatre and layout details."""

        skip = (page - 1) * size

        query = (
            select(
                ScreenModel.id,
                ScreenModel.name,
                ScreenModel.theatre_id,
                ScreenModel.layout_id,
                TheatreModel.name.label("theatre_name"),
                LayoutModel.name.label("layout_name"),
            )
            .join(TheatreModel, ScreenModel.theatre_id == TheatreModel.id)
            .join(LayoutModel, ScreenModel.layout_id == LayoutModel.id)
            .join(
                TheatreOperatorMapModel,
                TheatreOperatorMapModel.theatre_id == TheatreModel.id,
            )
            .where(
                ScreenModel.is_active == True,
                TheatreModel.is_active == True,
                TheatreOperatorMapModel.user_id == user_id,
            )
            .offset(skip)
            .limit(size)
        )

        result = await self.db.execute(query)
        return result.all()

    async def get_layout_by_screen_repo(self, screen_id: str):
        """Fetch layout for a screen if active."""
        query = (
            select(LayoutModel)
            .join(ScreenModel, ScreenModel.layout_id == LayoutModel.id)
            .where(ScreenModel.id == screen_id, ScreenModel.is_active == True)
        )

        result = await self.db.execute(query)

        return result.scalar_one_or_none()

    async def validate_screen_and_user(self, screen_id: str, user_id: str):
        """Fetch screen if it belongs to user and is active."""
        query = (
            select(ScreenModel)
            .join(TheatreModel, ScreenModel.theatre_id == TheatreModel.id)
            .join(
                TheatreOperatorMapModel,
                TheatreOperatorMapModel.theatre_id == TheatreModel.id,
            )
            .where(
                ScreenModel.id == screen_id,
                ScreenModel.is_active == True,
                TheatreModel.is_active == True,
                TheatreOperatorMapModel.user_id == user_id,
            )
        )

        result = await self.db.execute(query)

        return result.scalar_one_or_none()

    async def delete_screen_repo(self, screen_id: str, user_id: str):
        """Soft delete screen if it belongs to user."""
        query = (
            select(ScreenModel)
            .join(TheatreModel, ScreenModel.theatre_id == TheatreModel.id)
            .join(
                TheatreOperatorMapModel,
                TheatreOperatorMapModel.theatre_id == TheatreModel.id,
            )
            .where(
                ScreenModel.id == screen_id,
                ScreenModel.is_active == True,
                TheatreModel.is_active == True,
                TheatreOperatorMapModel.user_id == user_id,
            )
        )

        result = await self.db.execute(query)

        screen_found = result.scalar_one_or_none()

        if not screen_found:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Screen not found"
            )

        return await screen_found.soft_delete(db=self.db)
