from sqlalchemy.ext.asyncio import AsyncSession
from app.models import UserModel, RoleModel, RolePermissionMap, PermissionModel
from sqlalchemy import select
from uuid import UUID


class PermissionRepo:
    """Handle permission related database checks."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def permission_check_repo(self, user_id: str, permission: str) -> bool:
        """Check if user has required permission."""
        permission_check_query = (
            select(UserModel.id)
            .join(RolePermissionMap, UserModel.role_id == RolePermissionMap.role_id)
            .join(
                PermissionModel, RolePermissionMap.permission_id == PermissionModel.id
            )
            .where(
                UserModel.id == user_id,
                UserModel.is_active == True,
                PermissionModel.permission == permission,
            )
        )

        permission_check_result = await self.db.scalars(permission_check_query)

        if not permission_check_result.first():
            return False
        return True
