from sqlalchemy.ext.asyncio import AsyncSession
from app.models import UserModel, UserDetailModel, RoleModel
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from fastapi import HTTPException, status


class UserRepository:
    def __init__(
        self,
        db: AsyncSession
    ):

        self.db = db

    async def get_user_by_email_repo(
        self,
        email: str
    ) -> UserModel:
        
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

        return new_user

    async def get_user_id_by_email_and_role_repo(
        self,
        email: str,
        role: str
    ) -> UserModel:

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

    async def get_all_users_repo(
        self,
        page: int,
        size: int
    ):
        
        skip = (page - 1) * size
        result = await self.db.scalars(
            select(UserModel)
            .where(UserModel.is_active == True)
            .offset(skip)
            .limit(size)
        )
        return result.all()
    

    async def delete_user_repo(
        self,
        user_id: str
    ):
        
        query = select(
            UserModel
        ).where(
            UserModel.id == user_id,
            UserModel.is_active == True
        )

        result = await self.db.execute(
            query
        )

        user_found = result.scalar_one_or_none()

        if not user_found:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        await user_found.soft_delete(db=self.db)
