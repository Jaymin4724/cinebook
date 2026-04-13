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

    async def lock_seat_service(
        self,
        show_id: str,
        user_id: str,
        seat_array: list,
        seat_layout_service: SeatLayoutService,
    ):

        cached_layout = await self.redis.json().get(f"show_seat_layout_{show_id}")

        if not cached_layout:
            async with self.db.begin():
                seat_layout_service.db = self.db
                layout_body = await seat_layout_service.generate_show_layout(
                    show_id=show_id
                )
        else:
            layout_body = cached_layout

        if not layout_body:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Layout not found"
            )

        layout = layout_body.get("layout")
        seat_mapping = layout_body.get("seat_mapping")

        locked_seats = await self.redis.hgetall(f"show_seat_locked_{show_id}")

        async with self.redis.pipeline(transaction=True) as pipe:
            for seat in seat_array:

                seat_grid = seat_mapping.get(seat)

                if not seat_grid:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND, detail="Seat not found"
                    )

                row_idx, col_idx = seat_grid

                if (
                    layout[row_idx][col_idx].get("status") != "Available"
                    or seat in locked_seats
                ):
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"{seat} seat is not available",
                    )

                pipe.hsetnx(name=f"show_seat_locked_{show_id}", key=seat, value=user_id)

            result = await pipe.execute()

        if 0 in result:
            self.redis.hdel(f"show_seat_locked_{show_id}", *seat_array)

            pipe.hexpire(f"show_seat_locked_{show_id}", 600, *seat_array)

            pipe.expire(name=f"show_seat_locked_{show_id}", time=3600, nx=True)

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Seats are not available",
            )

        return create_response(message="Seats Locked")

    async def book_ticket_service(
        self,
        show_id: str,
        user_id: str,
        seat_array: list,
    ):

        locked_seats = await self.redis.hgetall(f"show_seat_locked_{show_id}")

        for seat in seat_array:
            current_locker = locked_seats.get(seat)
            if current_locker != user_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Seat {seat} is not locked by you or the lock has expired.",
                )

        async with self.db.begin():
            total_bill = 500.0 * len(seat_array)
            booking = await self.booking_repo.create_booking_repo(
                user_id=UUID(user_id),
                show_id=UUID(show_id),
                seat_array=seat_array,
                total_bill=total_bill,
            )

        cached_layout = await self.redis.json().get(f"show_seat_layout_{show_id}")
        if cached_layout:
            layout = cached_layout.get("layout")
            seat_mapping = cached_layout.get("seat_mapping")

            for seat in seat_array:
                row_idx, col_idx = seat_mapping[seat]
                layout[row_idx][col_idx]["status"] = "Booked"

            async with self.redis.pipeline(transaction=True) as pipe:
                pipe.json().set(f"show_seat_layout_{show_id}", "$", cached_layout)
                pipe.hdel(f"show_seat_locked_{show_id}", *seat_array)
                await pipe.execute()

        return create_response(
            message="Tickets Booked Successfully",
            data={
                "show_id": show_id,
                "seats": seat_array,
                "booking_id": str(booking.id),
            },
        )
