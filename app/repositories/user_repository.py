from sqlalchemy.ext.asyncio import AsyncSession
from app.models import UserModel, RoleModel
from sqlalchemy import select


class UserRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_user_by_email_repo(self, email: str) -> UserModel:

        query = select(UserModel).where(UserModel.email == email)
        result = await self.db.scalars(query)
        return result.first()

    async def create_new_user_repo(self, email: str, role: str = "user") -> UserModel:
        role_query = select(RoleModel).where(RoleModel.role == role)
        role_result = await self.db.scalars(role_query)
        role_obj = role_result.first()

        if not role_obj:
            raise ValueError(f"Role '{role}' not found in database")

        new_user = UserModel(email=email, is_verified=True, role_id=role_obj.id)

        self.db.add(new_user)
        await self.db.flush()

        return new_user