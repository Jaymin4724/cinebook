from sqlalchemy.ext.asyncio import AsyncSession
from app.models import UserModel, UserDetailModel, RoleModel
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from fastapi import HTTPException, status


class UserRepository:
    """Handle database operations related to users."""

    def __init__(self, db: AsyncSession):

        self.db = db

    async def get_user_by_email_repo(self, email: str) -> UserModel:
        """Fetch user by email with user details."""
        query = (
            select(UserModel)
            .where(UserModel.email == email)
            .options(selectinload(UserModel.user_detail))
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def create_new_user_repo(
        self,
        email: str,
        google_id: str = None,
        first_name: str = None,
        last_name: str = None,
        role: str = "user",
    ) -> UserModel:
        """Create a new user with role and basic details."""
        role_obj = (
            await self.db.execute(select(RoleModel).where(RoleModel.role == role))
        ).scalar_one_or_none()

        if not role_obj:
            raise ValueError(f"Role '{role}' not found")

        new_user = UserModel(
            email=email, google_id=google_id, role_id=role_obj.id, is_active=True
        )
        self.db.add(new_user)
        await self.db.flush()

        new_user_details = UserDetailModel(
            user_id=new_user.id, first_name=first_name, last_name=last_name
        )
        self.db.add(new_user_details)
        await self.db.flush()

        result = await self.db.execute(
            select(UserModel)
            .where(UserModel.id == new_user.id)
            .options(selectinload(UserModel.role), selectinload(UserModel.user_detail))
        )

        user_with_relations = result.scalar_one()

        return user_with_relations

    async def get_user_id_by_email_and_role_repo(
        self, email: str, role: str
    ) -> UserModel:
        """Fetch user ID by email and role if active."""
        query = (
            select(UserModel.id)
            .join(RoleModel, UserModel.role_id == RoleModel.id)
            .where(
                UserModel.email == email,
                UserModel.is_active == True,
                RoleModel.role == role,
            )
        )

        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_all_users_repo(self, page: int, size: int):
        """Fetch paginated list of active users."""
        skip = (page - 1) * size
        result = await self.db.scalars(
            select(UserModel)
            .where(UserModel.is_active == True)
            .options(selectinload(UserModel.role), selectinload(UserModel.user_detail))
            .offset(skip)
            .limit(size)
        )
        return result.all()

    async def delete_user_repo(self, user_id: str):
        """Soft delete user by ID if exists."""
        query = select(UserModel).where(
            UserModel.id == user_id, UserModel.is_active == True
        )

        result = await self.db.execute(query)

        user_found = result.scalar_one_or_none()

        if not user_found:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )

        return await user_found.soft_delete(db=self.db)

    async def get_user_by_id(self, user_id: str):

        query = select(UserModel).where(UserModel.id == user_id)

        result = await self.db.execute(query)

        user_found = result.scalar_one_or_none()

        if not user_found:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )

        return user_found
