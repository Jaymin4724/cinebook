from typing import Annotated
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends
from app.db.session import get_db
from app.core.redis_config import get_redis, Redis
from app.services.auth_service import AuthService
from app.repositories.user_repository import UserRepository
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.repositories.user_repository import UserRepository

DBDep = Annotated[AsyncSession, Depends(get_db)]
RedisDep = Annotated[Redis, Depends(get_redis)]
AuthServiceDep = Annotated[AuthService, Depends(AuthService)]
UserRepoDep = Annotated[UserRepository, Depends(UserRepository)]
