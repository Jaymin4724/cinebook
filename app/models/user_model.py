from sqlalchemy import String, ForeignKey, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base
from typing import TYPE_CHECKING
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession


if TYPE_CHECKING:
    from app.models import (
        RoleModel,
        UserDetailModel,
        TheatreOperatorMapModel,
        BookingModel,
    )


class UserModel(Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    google_id: Mapped[str | None] = mapped_column(
        String(255), unique=True, index=True, nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    role_id: Mapped[UUID] = mapped_column(ForeignKey("roles.id"), index=True)

    role: Mapped["RoleModel"] = relationship(back_populates="user_list")
    user_detail: Mapped["UserDetailModel"] = relationship(back_populates="user")
    theatre_operator_list: Mapped[list["TheatreOperatorMapModel"]] = relationship(
        back_populates="user"
    )
    booking_list: Mapped[list["BookingModel"]] = relationship(back_populates="user")

    async def soft_delete(self, db: AsyncSession):
        """Mark user as deleted."""
        self.is_active = False
        db.add(self)
        return self
