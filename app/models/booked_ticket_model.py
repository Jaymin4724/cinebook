from sqlalchemy import ForeignKey, DateTime, Boolean, LargeBinary, text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base
from uuid import UUID
from typing import TYPE_CHECKING
from datetime import datetime


if TYPE_CHECKING:
    from app.models import BookingModel


class BookedTicketModel(Base):
    __tablename__ = "booked_tickets"

    booking_id: Mapped[UUID] = mapped_column(ForeignKey("bookings.id"), index=True, unique=True)
    ticket_hash: Mapped[bytes] = mapped_column(LargeBinary, nullable=False, unique=True)
    expired_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    is_used: Mapped[bool] = mapped_column(Boolean, server_default="false")

    booking: Mapped["BookingModel"] = relationship(back_populates="booked_ticket")