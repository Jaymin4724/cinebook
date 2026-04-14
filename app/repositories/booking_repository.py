from sqlalchemy.ext.asyncio import AsyncSession
from app.models import BookingModel, BookedSeatMapModel
from uuid import UUID


class BookingRepository:
    """Handle database operations related to bookings."""
    def __init__(self, db: AsyncSession):
        self.db = db

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
