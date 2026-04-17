from sqlalchemy.ext.asyncio import AsyncSession
from app.models import BookedTicketModel
from datetime import datetime

class BookingTicketRepository:
    """Handle database operations related to bookings tickets."""
    def __init__(self, db: AsyncSession):
        self.db = db


    async def create_booking_ticket(
        self,
        booking_id: str,
        ticket_hash: str,
        expired_time: datetime
    ):
        
        new_ticket = BookedTicketModel(
            booking_id=booking_id,
            ticket_hash=ticket_hash,
            expired_time=expired_time.replace(tzinfo=None)
        )

        self.db.add(new_ticket)

        await self.db.flush()
        
        return new_ticket