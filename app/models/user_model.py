from sqlalchemy import String, ForeignKey, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base
from typing import TYPE_CHECKING
from uuid import UUID


if TYPE_CHECKING:
    from app.models import RoleModel,UserDetailModel,TheatreOperatorMapModel,BookingModel


class UserModel(Base):
    __tablename__ = "users"
    
    email : Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    is_active : Mapped[bool] = mapped_column(Boolean, default=True)
    is_verified : Mapped[bool] = mapped_column(Boolean, default=True)
    role_id : Mapped[UUID] = mapped_column(ForeignKey("roles.id"), index=True)

    role : Mapped["RoleModel"] = relationship(back_populates="user_list")
    user_detail : Mapped["UserDetailModel"] = relationship(back_populates="user")
    theatre_operator_list : Mapped[list["TheatreOperatorMapModel"]] = relationship(back_populates="user")
    booking_list : Mapped[list["BookingModel"]] = relationship(back_populates="user")