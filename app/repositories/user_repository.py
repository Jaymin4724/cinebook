from sqlalchemy.ext.asyncio import AsyncSession
from app.models import UserModel, RoleModel
from sqlalchemy import Select


class UserRepository:

    async def get_user_by_email_repo(self, email: str, db: AsyncSession) -> UserModel:

        get_user_by_email_query = Select(
            UserModel
        ).where(
            UserModel.email == email
        )

        get_user_by_email_query_result = await db.scalars(get_user_by_email_query)
        get_user_by_email = get_user_by_email_query_result.first()

        return get_user_by_email

    async def create_new_user_repo(self, email: str, db: AsyncSession, role: str = "user") -> UserModel:

        get_user_role_id_query = Select(
            RoleModel
        ).where(
            RoleModel.role == role
        )

        get_user_role_id_query_result = await db.scalars(get_user_role_id_query)
        get_user_role_id = get_user_role_id_query_result.first()

        new_user = UserModel(
            email=email,
            is_verified=True,
            role_id=get_user_role_id.id
        )

        db.add(new_user)

        await db.flush()

        return new_user