from sqlalchemy.ext.asyncio import AsyncSession
from app.models import BookedTicketModel, BookingModel, ShowModel, ScreenModel, TheatreModel, TheatreOperatorMapModel
from datetime import datetime, timezone
from sqlalchemy import select, update
from fastapi import HTTPException, status

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
    

    async def update_ticket_status(
        self,
        booking_id: str
    ):
        query = update(
            BookedTicketModel
        ).where(
            BookedTicketModel.booking_id == booking_id
        ).values(
            {"is_used": True}
        )

        await self.db.execute(query)
    

    async def validate_ticket_hash(
        self,
        booking_id: str,
    ):
        now = datetime.now(tz=timezone.utc).replace(tzinfo=None)

        query = select(
            BookedTicketModel
        ).where(
            BookedTicketModel.booking_id == booking_id,
            BookedTicketModel.expired_time >= now,
            BookedTicketModel.is_used == False
        )

        result = await self.db.execute(query)

        ticket_found = result.scalar_one_or_none()

        if not ticket_found:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ticket is not valid"
            )
        
        return ticket_found


    async def validate_ticket_and_theatre(
        self,
        booking_id: str,
        user_id: str
    ):
        
        query = select(
            BookedTicketModel
        ).join(
            BookingModel, BookedTicketModel.booking_id == BookingModel.id
        ).join(
            ShowModel, BookingModel.show_id == ShowModel.id
        ).join(
            ScreenModel, ShowModel.screen_id == ScreenModel.id
        ).join(
            TheatreOperatorMapModel, ScreenModel.theatre_id == TheatreOperatorMapModel.theatre_id
        ).where(
            BookedTicketModel.booking_id == booking_id,
            TheatreOperatorMapModel.user_id == user_id,
            ShowModel.is_deleted == False,
            ScreenModel.is_active == True
        )

        result = await self.db.execute(query)

        ticket_found = result.scalar_one_or_none()

        if not ticket_found:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ticket Not Found"
            )
        
        return ticket_found