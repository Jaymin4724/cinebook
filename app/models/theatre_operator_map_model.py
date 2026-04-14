from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base
from typing import TYPE_CHECKING
from uuid import UUID


if TYPE_CHECKING:
    from app.models import UserModel, TheatreModel


class TheatreOperatorMapModel(Base):
    __tablename__ = "theatre_operators_map"

    theatre_id: Mapped[UUID] = mapped_column(ForeignKey("theatres.id"), index=True)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), index=True)

    user: Mapped["UserModel"] = relationship(back_populates="theatre_operator_list")
    theatre: Mapped["TheatreModel"] = relationship(
        back_populates="theatre_operator_list"
    )
