from sqlalchemy import String, Boolean, Numeric, CheckConstraint, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates
from sqlalchemy.dialects.postgresql import INTERVAL, ARRAY
from app.db.base import Base
from typing import TYPE_CHECKING
from datetime import timedelta
import enum
from sqlalchemy.ext.asyncio import AsyncSession


if TYPE_CHECKING:
    from app.models import ShowModel


class MovieModel(Base):
    __tablename__ = "movies"

    name: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    duration: Mapped[timedelta] = mapped_column(INTERVAL)
    description: Mapped[str] = mapped_column(String)
    rating: Mapped[float] = mapped_column(
        Numeric(3, 1), CheckConstraint("rating >= 0 AND rating <= 10"), nullable=False
    )
    genre: Mapped[str] = mapped_column(String)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    imdb_id: Mapped[str] = mapped_column(String, nullable=False, unique=True)

    show_list: Mapped[list["ShowModel"]] = relationship(back_populates="movie")

    async def soft_delete(self, db: AsyncSession):
        """Mark movie as deleted."""
        self.is_deleted = True
        db.add(self)
        return self
