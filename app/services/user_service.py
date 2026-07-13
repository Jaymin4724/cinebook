from sqlalchemy.ext.asyncio import AsyncSession
from app.core.redis_config import Redis
from app.repositories.movie_repository import MovieRepository
from app.repositories.theatre_repository import TheatreRepository
from app.repositories.booking_repository import BookingRepository
from app.repositories.user_repository import UserRepository
from app.repositories.booked_ticket_repository import BookingTicketRepository

from app.repositories.show_repository import ShowRepository
from app.services.seat_layout_service import SeatLayoutService
from app.schemas.movie_schema import MovieOutSchema
from app.schemas.theatre_schema import TheatreOutSchema
from app.schemas.standard_schema import ResponseSchema, create_response
from app.schemas.show_schema import ShowDetailOutSchema
from app.schemas.booking_schema import BookingOutSchema, BookingDetailOutSchema
from app.schemas.user_schema import UserOutSchema
from fastapi import status, HTTPException, BackgroundTasks
from app.services.email_service import EmailService
from sqlalchemy.exc import IntegrityError

from app.utils.helper import encrypt_data
from app.utils.seat_lock_script import acquire_seat_locks

from uuid import UUID
from datetime import datetime, timedelta, timezone


class UserService:
    """Handle user related operations."""

    def __init__(
        self,
        db: AsyncSession,
        redis: Redis,
        movie_repo: MovieRepository,
        theatre_repo: TheatreRepository,
        show_repo: ShowRepository,
        booking_repo: BookingRepository,
        user_repo: UserRepository,
        booked_ticket_repo: BookingTicketRepository,
        email_service: EmailService
    ):
        self.db = db
        self.redis = redis
        self.movie_repo = movie_repo
        self.theatre_repo = theatre_repo
        self.show_repo = show_repo
        self.booking_repo = booking_repo
        self.user_repo = user_repo
        self.booked_ticket_repo = booked_ticket_repo
        self.email_service = email_service

    async def get_movies_by_theatre_service(
        self, theatre_id: str, page: int = 1, size: int = 10
    ) -> ResponseSchema:
        """Fetch movies running in a theatre."""
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
        """Fetch theatres showing a movie."""
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
        """Fetch shows for a movie in a theatre."""
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
        """Fetch show details with seat layout."""
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
        """Fetch or generate seat layout for a show."""
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
        """Fetch seat position and price from layout."""
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
        """Lock selected seats for a show."""
        layout_body = await self._get_layout(show_id, seat_layout_service)

        for seat in seat_array:
            row, col, _ = self._get_seat_info(layout_body, seat)

            is_available = (
                layout_body["layout"][row][col].get("status") == "Available"
            )
            if not is_available:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Seat {seat} is unavailable",
                )

        locked = await acquire_seat_locks(
            redis=self.redis,
            show_id=show_id,
            user_id=user_id,
            seat_array=seat_array,
        )
        if not locked:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="One or more seats were just locked by another user",
            )

        return create_response(message="Seats Locked Successfully")

    async def book_ticket_service(
        self,
        show_id: str,
        user_id: str,
        seat_array: list,
        seat_layout_service: SeatLayoutService,
        background_tasks: BackgroundTasks,
    ):
        """Book locked seats and create booking."""
        locked_seats = await self.redis.hgetall(f"show_seat_locked_{show_id}")
        for seat in seat_array:
            if locked_seats.get(seat) != user_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Seat {seat} lock expired or invalid",
                )

        layout_body = await self._get_layout(show_id, seat_layout_service)
        total_bill = 0
        for seat in seat_array:
            _, _, price = self._get_seat_info(layout_body, seat)
            total_bill += price

        try:
            async with self.db.begin():
                self.show_repo.db = self.db
                self.booking_repo.db = self.db

                already_booked = await self.booking_repo.get_booked_seats_repo(
                    show_id=UUID(show_id), seat_array=seat_array
                )
                if already_booked:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=f"Seat(s) {', '.join(already_booked)} already booked",
                    )

                booking = await self.booking_repo.create_booking_repo(
                    user_id=UUID(user_id),
                    show_id=UUID(show_id),
                    seat_array=seat_array,
                    total_bill=total_bill,
                )

                booking_id = booking.id

                show_end_time = await self.show_repo.get_show_end_time(
                    show_id=show_id
                )

                ticket_hash = await encrypt_data(data=str(booking_id))

                ticket = await self.booked_ticket_repo.create_booking_ticket(
                    booking_id=booking_id,
                    expired_time=show_end_time,
                    ticket_hash=ticket_hash
                )

                user = await self.user_repo.get_user_by_id(
                    user_id=user_id
                )
        except IntegrityError:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="One or more seats were already booked by someone else",
            )

        background_tasks.add_task(
            self.email_service.send_qr_ticket,
            email_to=user.email,
            ticket_hash=ticket_hash,
        )

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

    async def get_booking_history_service(
        self, user_id: str, page: int = 1, size: int = 10
    ) -> ResponseSchema:
        """Fetch paginated booking history for the current user."""
        async with self.db.begin():
            self.booking_repo.db = self.db
            bookings = await self.booking_repo.get_bookings_by_user_repo(
                user_id=UUID(user_id), page=page, size=size
            )

        bookings_data = [
            BookingOutSchema.model_validate(booking).model_dump(mode="json")
            for booking in bookings
        ]
        return create_response(
            data=bookings_data, message="Booking history fetched successfully"
        )

    async def get_booking_detail_service(
        self, booking_id: str, user_id: str
    ) -> ResponseSchema:
        """Fetch a single booking's details for the current user."""
        async with self.db.begin():
            self.booking_repo.db = self.db
            booking = await self.booking_repo.get_booking_by_id_repo(
                booking_id=UUID(booking_id), user_id=UUID(user_id)
            )

        booking_data = BookingDetailOutSchema.model_validate(booking).model_dump(
            mode="json"
        )
        return create_response(
            data=booking_data, message="Booking detail fetched successfully"
        )

    async def cancel_booking_service(
        self, booking_id: str, user_id: str
    ) -> ResponseSchema:
        """Cancel a booking and release its seats, if within the allowed window."""
        async with self.db.begin():
            self.booking_repo.db = self.db
            booking = await self.booking_repo.get_booking_by_id_repo(
                booking_id=UUID(booking_id), user_id=UUID(user_id)
            )

            if booking.is_cancelled:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Booking is already cancelled",
                )

            show_start_time = booking.show.start_time.replace(tzinfo=timezone.utc)
            if show_start_time - datetime.now(timezone.utc) < timedelta(hours=6):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Booking can only be cancelled at least 6 hours before the show",
                )

            cancelled_seats = [seat.seats_number for seat in booking.booked_seat_list]
            show_id = str(booking.show_id)

            await self.booking_repo.cancel_booking_repo(booking=booking)

        layout_body = await self.redis.json().get(f"show_seat_layout_{show_id}")
        if layout_body:
            seat_mapping = layout_body.get("seat_mapping", {})
            for seat in cancelled_seats:
                seat_grid = seat_mapping.get(seat)
                if seat_grid:
                    row, col = seat_grid
                    layout_body["layout"][row][col]["status"] = "Available"
            await self.redis.json().set(
                name=f"show_seat_layout_{show_id}", path="$", obj=layout_body
            )

        return create_response(message="Booking cancelled successfully")

    async def get_profile_service(self, user_id: str) -> ResponseSchema:
        """Fetch the current user's profile."""
        async with self.db.begin():
            self.user_repo.db = self.db
            user = await self.user_repo.get_user_profile_repo(user_id=UUID(user_id))

        user_data = UserOutSchema.model_validate(user).model_dump(mode="json")
        return create_response(data=user_data, message="Profile fetched successfully")

    async def update_profile_service(
        self, user_id: str, update_data: dict
    ) -> ResponseSchema:
        """Update the current user's profile details."""
        async with self.db.begin():
            self.user_repo.db = self.db
            user = await self.user_repo.update_user_detail_repo(
                user_id=UUID(user_id), update_data=update_data
            )

        user_data = UserOutSchema.model_validate(user).model_dump(mode="json")
        return create_response(data=user_data, message="Profile updated successfully")

    async def delete_user_service(self, user_id: str):
        """Delete user account."""
        async with self.db.begin():
            self.user_repo.db = self.db

            await self.user_repo.delete_user_repo(user_id=user_id)

        return create_response(message="User deleted successfully")
