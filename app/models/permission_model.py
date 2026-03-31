from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from app.models import RolePermissionMap


class PermissionModel(Base):
    __tablename__ = "permissions"

    permission: Mapped[str] = mapped_column(String(50))

    role_permission_list: Mapped[list["RolePermissionMap"]] = relationship(back_populates="permission")