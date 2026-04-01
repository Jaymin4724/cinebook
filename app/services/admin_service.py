from sqlalchemy.ext.asyncio import AsyncSession
from app.utils.helper import validate_otp
from app.core.redis_config import Redis
from app.repositories.user_repository import UserRepository
from app.schemas.standard_schema import ResponseSchema, create_response


class AdminService:
    
    def __init__(self, db: AsyncSession, redis: Redis, user_repo: UserRepository = None):
        self.db = db
        self.redis = redis
        self.user_repo = user_repo


    async def create_user_service(self, user_body: dict) -> ResponseSchema:

        user_email = user_body.get("email")
        otp = user_body.get("otp")
        role = user_body.get("role")
        if user_email and otp:
            validate_otp(
                email=user_email,
                otp=otp,
                redis=self.redis
            )

        async with self.db.begin():
            self.user_repo.db = self.db

            await self.user_repo.create_new_user_repo(
                email=user_email,
                role=role
            )

        return create_response(message=f"User created successfully with role {role}")
        