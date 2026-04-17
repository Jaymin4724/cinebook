from sqlalchemy import ForeignKey, Float, ARRAY, Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base
from uuid import UUID
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from app.models import UserModel,ShowModel,BookedSeatMapModel,BookedTicketModel


class BookingModel(Base):
    __tablename__ = "bookings"

    total_bill : Mapped[float] = mapped_column(Float, nullable=False)
    number_of_seats : Mapped[int] = mapped_column(Integer, nullable=False)
    user_id : Mapped[UUID] = mapped_column(ForeignKey("users.id"), index=True)
    show_id : Mapped[UUID] = mapped_column(ForeignKey("shows.id"), index=True)
    is_cancelled : Mapped[bool] = mapped_column(Boolean, default=False)

    user : Mapped["UserModel"] = relationship(back_populates="booking_list")
    show : Mapped["ShowModel"] = relationship(back_populates="booking_list")
    booked_seat_list: Mapped[list["BookedSeatMapModel"]] = relationship(back_populates="booking")
    booked_ticket: Mapped["BookedTicketModel"] = relationship(back_populates="booking")