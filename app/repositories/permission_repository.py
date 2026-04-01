from sqlalchemy.ext.asyncio import AsyncSession
from app.models import UserModel, RoleModel, RolePermissionMap, PermissionModel
from sqlalchemy import select
from uuid import UUID


class PermissionRepo:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def permission_check_repo(self, user_id: str, permission: str) -> bool:

        permission_check_query = select(
            UserModel.id
        ).join(
            UserModel.role_id == RolePermissionMap.role_id
        ).join(
            RolePermissionMap.permission_id == PermissionModel.id
        ).where(
            UserModel.id == UUID(user_id),
            PermissionModel.permission == permission 
        )
        
        permission_check_result = await self.db.scalars(permission_check_query)

        if not permission_check_result.first():
            return False
        return True