from sqlalchemy import String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base
from typing import TYPE_CHECKING
from uuid import UUID


if TYPE_CHECKING:
    from app.models import UserModel


class UserDetailModel(Base):
    __tablename__ = "user_details"

    first_name: Mapped[str | None] = mapped_column(
        String(50), nullable=True, default=None
    )
    last_name: Mapped[str | None] = mapped_column(
        String(50), nullable=True, default=None
    )
    mobile_no: Mapped[str | None] = mapped_column(
        String(50), nullable=True, default=None
    )

    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), index=True)

    user: Mapped["UserModel"] = relationship(back_populates="user_detail")
