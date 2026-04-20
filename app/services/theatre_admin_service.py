from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis
from app.repositories.layout_repository import LayoutRepository
from app.repositories.screen_repository import ScreenRepository
from app.repositories.theatre_repository import TheatreRepository
from app.repositories.movie_repository import MovieRepository
from app.repositories.show_repository import ShowRepository
from app.repositories.booked_ticket_repository import BookingTicketRepository
from app.schemas.standard_schema import ResponseSchema, create_response
from app.schemas.screen_schema import ScreenOutSchema, ScreenWithDetailsSchema
from app.schemas.theatre_schema import TheatreOutSchema
from app.schemas.show_schema import ShowOutSchema

from fastapi import HTTPException, status
from app.utils.polish_seat_layout import polish_seat_layout
from app.utils.show_create_validation import (
    validate_start_time_of_show,
    validate_category_price,
    validate_movie_and_return_time,
    validate_show_overlap,
)
from app.utils.helper import decrypt_data
from datetime import timezone, timedelta, datetime


class TheatreAdminService:
    """Handle theatre admin operations."""

    def __init__(
        self,
        db: AsyncSession,
        redis: Redis,
        layout_repo: LayoutRepository,
        screen_repo: ScreenRepository,
        theatre_repo: TheatreRepository,
        movie_repo: MovieRepository,
        show_repo: ShowRepository,
        booked_ticket_repo: BookingTicketRepository
    ):

        self.db = db
        self.redis = redis
        self.layout_repo = layout_repo
        self.screen_repo = screen_repo
        self.theatre_repo = theatre_repo
        self.movie_repo = movie_repo
        self.show_repo = show_repo
        self.booked_ticket_repo = booked_ticket_repo

    async def create_layout_service(
        self, layout_body: dict, user_id: str
    ) -> ResponseSchema:
        """Validate and create seat layout for a theatre."""
        layout_name = layout_body.get("name")
        layout_format = layout_body.get("layout")
        theatre_id = layout_body.get("theatre_id")

        async with self.db.begin():
            self.theatre_repo.db = self.db
            self.layout_repo.db = self.db

            theatre_found = await self.theatre_repo.get_theatre_by_id_and_user(
                theatre_id=theatre_id, user_id=user_id
            )

            if not theatre_found:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Theatre not found"
                )

            new_layout = polish_seat_layout(layout_format)

            if new_layout is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Layout format is not valid",
                )

            new_layout = await self.layout_repo.create_layout_repository(
                name=layout_name, layout=new_layout, theatre_id=theatre_id
            )

        return create_response(
            data={"id": new_layout.id, "layout": new_layout.layout},
            message="New layout created successfully",
        )

    async def create_screen_service(
        self, screen_body: dict, user_id: str
    ) -> ResponseSchema:
        """Validate and create screen for a theatre."""
        screen_name = screen_body.get("name")
        theatre_id = screen_body.get("theatre_id")
        layout_id = screen_body.get("layout_id")

        async with self.db.begin():
            self.theatre_repo.db = self.db
            self.layout_repo.db = self.db

            theatre_found = await self.theatre_repo.get_theatre_by_id_and_user(
                theatre_id=theatre_id, user_id=user_id
            )

            if not theatre_found:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Theatre not found"
                )

            layout_found = await self.layout_repo.get_layout_by_id_and_theatre(
                layout_id=layout_id, theatre_id=theatre_id
            )

            if not layout_found:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Layout not found"
                )

            new_screen = await self.screen_repo.create_screen_repo(
                name=screen_name, theatre_id=theatre_id, layout_id=layout_id
            )

        screen_data = ScreenOutSchema.model_validate(new_screen).model_dump(mode="json")
        return create_response(data=screen_data, message="Screen created successfully")

    async def create_show_service(
        self, show_body: dict, user_id: str
    ) -> ResponseSchema:
        """Validate and create show for a screen."""
        start_time = show_body.get("start_time").replace(tzinfo=timezone.utc)
        screen_id = show_body.get("screen_id")
        movie_id = show_body.get("movie_id")
        category_price = show_body.get("category_price")

        async with self.db.begin():
            self.screen_repo.db = self.db
            self.movie_repo.db = self.db
            self.show_repo.db = self.db
            self.layout_repo.db = self.db

            screen_found = await self.screen_repo.validate_screen_and_user(
                screen_id=screen_id, user_id=user_id
            )

            if not screen_found:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Screen not found"
                )

            movie_time_seconds = await validate_movie_and_return_time(
                movie_id=movie_id, movie_repo=self.movie_repo
            )

            movie_time = timedelta(seconds=movie_time_seconds)

            await validate_start_time_of_show(
                show_datetime=start_time,
            )

            await validate_show_overlap(
                start_time=start_time,
                movie_duration=movie_time,
                screen_id=screen_id,
                show_repo=self.show_repo,
            )

            await validate_category_price(
                category_price=category_price,
                screen_id=screen_id,
                screen_repo=self.screen_repo,
            )

            new_show = await self.show_repo.create_show_repo(
                start_time=start_time,
                screen_id=screen_id,
                movie_id=movie_id,
                category_pricing=category_price,
            )

            show_data = ShowOutSchema.model_validate(new_show).model_dump(mode="json")
        return create_response(data=show_data, message="Show created successfully")

    async def get_my_theatres_service(self, user_id: str, page: int, size: int):
        """Fetch all theatres mapped to the given user."""
        async with self.db.begin():
            self.theatre_repo.db = self.db

            theatres = await self.theatre_repo.get_all_theatres_by_user_repo(
                user_id=user_id, page=page, size=size
            )

            theatres_data = [
                TheatreOutSchema.model_validate(t).model_dump(mode="json")
                for t in theatres
            ]

        return create_response(
            data=theatres_data, message="Theatres fetched successfully"
        )

    async def get_my_screens_service(self, user_id: str, page: int, size: int):
        """Fetch all screens mapped to the given user."""

        async with self.db.begin():
            self.screen_repo.db = self.db

            screens = await self.screen_repo.get_all_screens_by_user_repo(
                user_id=user_id, page=page, size=size
            )

            screens_data = [
                ScreenWithDetailsSchema.model_validate(screen).model_dump(mode="json")
                for screen in screens
            ]

        return create_response(
            data=screens_data, message="Screens fetched successfully"
        )

    async def delete_screen_service(self, screen_id: str, user_id: str):
        """Delete screen by ID after validation."""
        async with self.db.begin():
            self.screen_repo.db = self.db

            deleted_screen = await self.screen_repo.delete_screen_repo(
                screen_id=screen_id, user_id=user_id
            )
            screen_data = ScreenOutSchema.model_validate(deleted_screen).model_dump(
                mode="json"
            )

        return create_response(data=screen_data, message="Screen deleted successfully")

    async def delete_show_service(self, show_id: str, user_id: str):
        """Delete show by ID after validation."""
        async with self.db.begin():
            self.show_repo.db = self.db

            deleted_show = await self.show_repo.delete_show_repo(
                show_id=show_id, user_id=user_id
            )
            
            show_data = ShowOutSchema.model_validate(deleted_show).model_dump(
                mode="json"
            )
        return create_response(data=show_data, message="Show deleted successfully")


    async def verify_ticket_service(
        self,
        user_id: str,
        ticket_hash: str
    ):

        ticket_hash = ticket_hash.encode()

        booking_id = await decrypt_data(encrypted_data=ticket_hash)

        async with self.db.begin():
            self.booked_ticket_repo.db = self.db

            await self.booked_ticket_repo.validate_ticket_hash(
                booking_id=booking_id
            )

            await self.booked_ticket_repo.validate_ticket_and_theatre(
                booking_id=booking_id,
                user_id=user_id
            )

            await self.booked_ticket_repo.update_ticket_status(
                booking_id=booking_id
            )
        
        return create_response(
            message="Ticket verified successfully"
        )
