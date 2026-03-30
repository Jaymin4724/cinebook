from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base
from typing import TYPE_CHECKING
from uuid import UUID


if TYPE_CHECKING:
    from app.models import RoleModel, PermissionModel

class RolePermissionMap(Base):
    __tablename__ = "roles_permissions_map"

    role_id: Mapped[UUID] = mapped_column(ForeignKey("roles.id"), index=True)
    permission_id: Mapped[UUID] = mapped_column(ForeignKey("permissions.id"), index=True)

    role: Mapped["RoleModel"] = relationship(back_populates="role_permission_list")
    permission: Mapped["PermissionModel"] = relationship(back_populates="role_permission_list")