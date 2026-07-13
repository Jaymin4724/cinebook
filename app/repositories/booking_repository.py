from sqlalchemy import select, desc
from sqlalchemy.orm import joinedload, selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from app.models import BookingModel, BookedSeatMapModel, ShowModel, ScreenModel
from uuid import UUID


class BookingRepository:
    """Handle database operations related to bookings."""
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_booked_seats_repo(
        self, show_id: UUID, seat_array: list[str]
    ) -> list[str]:
        """Return which of the given seats are already booked (non-cancelled) for a show."""
        query = select(BookedSeatMapModel.seats_number).where(
            BookedSeatMapModel.show_id == show_id,
            BookedSeatMapModel.seats_number.in_(seat_array),
            BookedSeatMapModel.is_cancelled == False,
        )
        result = await self.db.execute(query)
        return result.scalars().all()

    async def create_booking_repo(
        self, user_id: UUID, show_id: UUID, seat_array: list[str], total_bill: float
    ) -> BookingModel:
        """Create booking and store selected seats."""
        new_booking = BookingModel(
            user_id=user_id,
            show_id=show_id,
            number_of_seats=len(seat_array),
            total_bill=total_bill,
        )
        self.db.add(new_booking)
        await self.db.flush()

        booked_seats = [
            BookedSeatMapModel(
                seats_number=seat, booking_id=new_booking.id, show_id=show_id
            )
            for seat in seat_array
        ]
        self.db.add_all(booked_seats)
        return new_booking

    async def get_bookings_by_user_repo(
        self, user_id: UUID, page: int = 1, size: int = 10
    ) -> list[BookingModel]:
        """Fetch paginated booking history for a user, newest first."""
        offset = (page - 1) * size

        query = (
            select(BookingModel)
            .where(BookingModel.user_id == user_id)
            .options(
                joinedload(BookingModel.show).joinedload(ShowModel.movie),
                joinedload(BookingModel.show)
                .joinedload(ShowModel.screen)
                .joinedload(ScreenModel.theatre),
            )
            .order_by(desc(BookingModel.created_at))
            .offset(offset)
            .limit(size)
        )

        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_booking_by_id_repo(
        self, booking_id: UUID, user_id: UUID
    ) -> BookingModel:
        """Fetch a single booking owned by the user, with show and seat details."""
        query = (
            select(BookingModel)
            .where(BookingModel.id == booking_id, BookingModel.user_id == user_id)
            .options(
                joinedload(BookingModel.show).joinedload(ShowModel.movie),
                joinedload(BookingModel.show)
                .joinedload(ShowModel.screen)
                .joinedload(ScreenModel.theatre),
                selectinload(BookingModel.booked_seat_list),
            )
        )

        result = await self.db.execute(query)
        booking_found = result.scalar_one_or_none()

        if not booking_found:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found"
            )

        return booking_found

    async def cancel_booking_repo(self, booking: BookingModel) -> BookingModel:
        """Mark a booking and its seats as cancelled."""
        booking.is_cancelled = True
        for seat in booking.booked_seat_list:
            seat.is_cancelled = True

        self.db.add(booking)
        return booking
