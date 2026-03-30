from sqlalchemy import String, Boolean, Numeric, CheckConstraint, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import INTERVAL, ARRAY
from app.db.base import Base
from typing import TYPE_CHECKING
from datetime import timedelta
import enum


if TYPE_CHECKING:
    from app.models import ShowModel


class MovieGenre(enum.Enum):
    ACTION = "action"
    SCIFI = "sci-fi"
    COMEDY = "comedy"
    THRILLER = "thriller"
    ROMANCE = "romance"
    DRAMA = "drama"
    ANIMATION = "animation"
    CRIME = "crime"
    HORROR = "horror"
    FANTASY = "fantasy"
    OTHER = "other"


class MovieModel(Base):
    __tablename__ = "movies"
    
    name : Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    duration : Mapped[timedelta] = mapped_column(INTERVAL)
    description : Mapped[str] = mapped_column(String)
    rating : Mapped[float] = mapped_column(
        Numeric(3,1),
        CheckConstraint('rating >= 0 AND rating <= 10'),
        nullable=False
    )
    genre : Mapped[list[MovieGenre]] = mapped_column(
        ARRAY(Enum(MovieGenre, name="movie_genre_enum"))
    )
    is_deleted : Mapped[bool] = mapped_column(Boolean, default=False)

    show_list : Mapped[list["ShowModel"]] = relationship(back_populates="movie")