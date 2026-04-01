from typing import Annotated
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends
from app.db.session import get_db
from app.core.redis_config import get_redis, Redis
from app.services.auth_service import AuthService
from app.repositories.user_repository import UserRepository

DBDep = Annotated[AsyncSession, Depends(get_db)]
RedisDep = Annotated[Redis, Depends(get_redis)]


def get_user_repo(db: DBDep) -> UserRepository:
    return UserRepository(db=db)


UserRepoDep = Annotated[UserRepository, Depends(get_user_repo)]


def get_auth_service(redis: RedisDep, user_repo: UserRepoDep) -> AuthService:
    return AuthService(redis=redis, user_repo=user_repo)


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
