from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.layout_repository import LayoutRepository
from app.repositories.screen_repository import ScreenRepository
from app.repositories.theatre_repository import TheatreRepository
from app.schemas.standard_schema import ResponseSchema, create_response
from fastapi import HTTPException, status
from app.utils.polish_seat_layout import polish_seat_layout


class TheatreAdminService:
    
    def __init__(
        self,
        db: AsyncSession,
        layout_repo: LayoutRepository,
        screen_repo: ScreenRepository,
        theatre_repo: TheatreRepository
    ):
        self.db = db
        self.layout_repo = layout_repo
        self.screen_repo = screen_repo
        self.theatre_repo = theatre_repo


    async def create_layout_service(
        self,
        layout_body: dict,
        user_id: str
    ) -> ResponseSchema:
        
        layout_name = layout_body.get("name")
        layout_format = layout_body.get("layout")
        theatre_id = layout_body.get("theatre_id")

        async with self.db.begin():
            self.theatre_repo.db = self.db
            self.layout_repo.db = self.db

            theatre_found = await self.theatre_repo.get_theatre_by_id_and_user(
                theatre_id=theatre_id,
                user_id=user_id
            )

            if not theatre_found:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Theatre not found")
            
            new_layout = polish_seat_layout(layout=layout_format)

            if new_layout is None:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Layout format is not valid")

            await self.layout_repo.create_layout_repository(
                name=layout_name,
                layout=new_layout,
                theatre_id=theatre_id
            )

        return create_response(
            message="New layout created successfully"
        )
    
    async def create_screen_service(
        self,
        screen_body: dict,
        user_id: str
    ) -> ResponseSchema:
        
        screen_name = screen_body.get("name")
        theatre_id = screen_body.get("theatre_id")
        layout_id = screen_body.get("layout_id")

        async with self.db.begin():
            self.theatre_repo.db = self.db
            self.layout_repo.db = self.db

            theatre_found = await self.theatre_repo.get_theatre_by_id_and_user(
                theatre_id=theatre_id,
                user_id=user_id
            )

            if not theatre_found:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Theatre not found")
        
            await self.screen_repo.create_screen_repository(
                name=screen_name,
                theatre_id=theatre_id,
                layout_id=layout_id
            )

        return create_response(message="Screen created successfully")