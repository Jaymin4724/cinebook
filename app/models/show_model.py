from sqlalchemy import ForeignKey, DateTime, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base
from uuid import UUID
from datetime import datetime
from typing import TYPE_CHECKING, Dict, Any, Optional
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession


if TYPE_CHECKING:
    from app.models import ScreenModel, MovieModel, BookingModel, BookedSeatMapModel


class ShowModel(Base):
    __tablename__ = "shows"

    start_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    screen_id: Mapped[UUID] = mapped_column(ForeignKey("screens.id"), index=True)
    movie_id: Mapped[UUID] = mapped_column(ForeignKey("movies.id"), index=True)
    category_pricing: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB, nullable=False
    )
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)

    screen: Mapped["ScreenModel"] = relationship(back_populates="show_list")
    movie: Mapped["MovieModel"] = relationship(back_populates="show_list")
    booking_list: Mapped[list["BookingModel"]] = relationship(back_populates="show")
    booked_seat_list: Mapped["BookedSeatMapModel"] = relationship(back_populates="show")

    async def soft_delete(self, db: AsyncSession):
        self.is_deleted = True
        db.add(self)
        return self
