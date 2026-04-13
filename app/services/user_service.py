from sqlalchemy.ext.asyncio import AsyncSession
from app.core.redis_config import Redis
from app.repositories.movie_repository import MovieRepository
from app.repositories.theatre_repository import TheatreRepository
from app.repositories.booking_repository import BookingRepository

from app.repositories.show_repository import ShowRepository
from app.services.seat_layout_service import SeatLayoutService
from app.schemas.movie_schema import MovieOutSchema
from app.schemas.theatre_schema import TheatreOutSchema
from app.schemas.standard_schema import ResponseSchema, create_response
from app.schemas.show_schema import ShowDetailOutSchema
from fastapi import status, HTTPException

from uuid import UUID


class UserService:
    def __init__(
        self,
        db: AsyncSession,
        redis: Redis,
        movie_repo: MovieRepository,
        theatre_repo: TheatreRepository,
        show_repo: ShowRepository,
        booking_repo: BookingRepository,
    ):
        self.db = db
        self.redis = redis
        self.movie_repo = movie_repo
        self.theatre_repo = theatre_repo
        self.show_repo = show_repo
        self.booking_repo = booking_repo

    async def get_movies_by_theatre_service(
        self, theatre_id: str, page: int = 1, size: int = 10
    ) -> ResponseSchema:
        """Fetch all movies currently showing in a specific theatre."""
        async with self.db.begin():
            self.movie_repo.db = self.db
            movies = await self.movie_repo.get_movies_by_theatre_repo(
                theatre_id=theatre_id, page=page, size=size
            )

        movies_data = [
            MovieOutSchema.model_validate(movie).model_dump(mode="json")
            for movie in movies
        ]
        return create_response(
            data=movies_data,
            message="Movies for the specified theatre fetched successfully",
        )

    async def get_theatres_by_movie_service(
        self, movie_id: str, page: int = 1, size: int = 10
    ) -> ResponseSchema:
        """Fetch all theatres that are currently screening a specific movie."""
        async with self.db.begin():
            self.theatre_repo.db = self.db
            theatres = await self.theatre_repo.get_theatres_by_movie_repo(
                movie_id=movie_id, page=page, size=size
            )

        theatres_data = [
            TheatreOutSchema.model_validate(theatre).model_dump(mode="json")
            for theatre in theatres
        ]
        return create_response(
            data=theatres_data,
            message="Theatres screening this movie fetched successfully",
        )

    async def get_shows_service(
        self, theatre_id: str, movie_id: str, page: int = 1, size: int = 10
    ) -> ResponseSchema:
        """Fetch all specific show timings for a movie at a particular theatre."""
        async with self.db.begin():
            self.show_repo.db = self.db
            shows = await self.show_repo.get_shows_repo(
                theatre_id=theatre_id, movie_id=movie_id, page=page, size=size
            )

        shows_data = [
            ShowDetailOutSchema.model_validate(show).model_dump(mode="json")
            for show in shows
        ]

        return create_response(
            data=shows_data,
            message="Available shows for this movie and theatre fetched successfully",
        )

    async def get_show_details_service(
        self, show_id: str, seat_layout_service: SeatLayoutService
    ) -> ResponseSchema:
        async with self.db.begin():
            self.show_repo.db = self.db
            show = await self.show_repo.get_show_by_id_repo(
                show_id=show_id,
                seat_layout_service=seat_layout_service,
            )

            if not show:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Show not found or unavailable",
                )

        return create_response(data=show, message="Show details fetched successfully")

    async def _get_layout(self, show_id: str, seat_layout_service: SeatLayoutService):
        layout_body = await self.redis.json().get(f"show_seat_layout_{show_id}")

        if not layout_body:
            async with self.db.begin():
                seat_layout_service.db = self.db
                layout_body = await seat_layout_service.generate_show_layout(
                    show_id=show_id
                )

        if not layout_body:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Layout not found"
            )
        return layout_body

    def _get_seat_info(self, layout_body: dict, seat_id: str):
        mapping = layout_body.get("seat_mapping", {})
        layout = layout_body.get("layout", [])

        if seat_id not in mapping:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Seat {seat_id} not found",
            )

        row, col = mapping[seat_id]
        seat_data = layout[row][col]
        return row, col, seat_data.get("price", 0)

    async def lock_seat_service(
        self,
        show_id: str,
        user_id: str,
        seat_array: list,
        seat_layout_service: SeatLayoutService,
    ):
        layout_body = await self._get_layout(show_id, seat_layout_service)
        locked_seats = await self.redis.hgetall(f"show_seat_locked_{show_id}")

        async with self.redis.pipeline(transaction=True) as pipe:
            for seat in seat_array:
                row, col, _ = self._get_seat_info(layout_body, seat)

                is_available = (
                    layout_body["layout"][row][col].get("status") == "Available"
                )
                if not is_available or seat in locked_seats:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Seat {seat} is unavailable",
                    )

                pipe.hsetnx(f"show_seat_locked_{show_id}", seat, user_id)

            results = await pipe.execute()

        if 0 in results:
            await self.redis.hdel(f"show_seat_locked_{show_id}", *seat_array)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="One or more seats were just locked by another user",
            )

        await self.redis.expire(f"show_seat_locked_{show_id}", 600)
        return create_response(message="Seats Locked Successfully")

    async def book_ticket_service(self, show_id: str, user_id: str, seat_array: list):
        locked_seats = await self.redis.hgetall(f"show_seat_locked_{show_id}")
        for seat in seat_array:
            if locked_seats.get(seat) != user_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Seat {seat} lock expired or invalid",
                )

        layout_body = await self.redis.json().get(f"show_seat_layout_{show_id}")
        total_bill = 0
        for seat in seat_array:
            _, _, price = self._get_seat_info(layout_body, seat)
            total_bill += price

        async with self.db.begin():
            booking = await self.booking_repo.create_booking_repo(
                user_id=UUID(user_id),
                show_id=UUID(show_id),
                seat_array=seat_array,
                total_bill=total_bill,
            )

        if layout_body:
            for seat in seat_array:
                row, col, _ = self._get_seat_info(layout_body, seat)
                layout_body["layout"][row][col]["status"] = "Booked"

            async with self.redis.pipeline(transaction=True) as pipe:
                pipe.json().set(f"show_seat_layout_{show_id}", "$", layout_body)
                pipe.hdel(f"show_seat_locked_{show_id}", *seat_array)
                await pipe.execute()

        return create_response(
            message="Tickets Booked Successfully",
            data={"booking_id": str(booking.id), "total_paid": total_bill},
        )
