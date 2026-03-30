from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from app.models import UserModel,RolePermissionMap


class RoleModel(Base):
    __tablename__ = "roles"

    role: Mapped[str] = mapped_column(String(50))

    user_list : Mapped[list["UserModel"]] = relationship(back_populates="role")
    role_permission_list: Mapped[list["RolePermissionMap"]] = relationship(back_populates="role")