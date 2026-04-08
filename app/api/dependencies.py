from typing import Annotated
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends, HTTPException
from app.core.redis_config import get_redis, Redis
from app.db.session import get_db
from fastapi import Header, status
from app.utils.helper import decode_token
from app.core.config import settings
from sqlalchemy import select

from app.services.auth_service import AuthService
from app.services.admin_service import AdminService
from app.services.theatre_admin_service import TheatreAdminService
from app.services.email_service import EmailService

from app.repositories.user_repository import UserRepository
from app.repositories.permission_repository import PermissionRepo
from app.repositories.theatre_repository import TheatreRepository
from app.repositories.movie_repository import MovieRepository
from app.repositories.layout_repository import LayoutRepository
from app.repositories.screen_repository import ScreenRepository
from app.repositories.show_repository import ShowRepository


DBDep = Annotated[AsyncSession, Depends(get_db)]
RedisDep = Annotated[Redis, Depends(get_redis)]
EmailServiceDep = Annotated[EmailService, Depends(EmailService)]


def get_user_repo(db: DBDep) -> UserRepository:
    return UserRepository(db=db)


def get_permission_repo(db: DBDep) -> PermissionRepo:
    return PermissionRepo(db=db)


def get_theatre_repo(db: DBDep) -> TheatreRepository:
    return TheatreRepository(db=db)


def get_movie_repo(db: DBDep) -> MovieRepository:
    return MovieRepository(db=db)


def get_layout_repo(db: DBDep) -> LayoutRepository:
    return LayoutRepository(db=db)


def get_screen_repo(db: DBDep) -> ScreenRepository:
    return ScreenRepository(db=db)

def get_show_repo(db: DBDep) -> ShowRepository:
    return ShowRepository(db=db)


UserRepoDep = Annotated[UserRepository, Depends(get_user_repo)]
PermissionRepoDep = Annotated[PermissionRepo, Depends(get_permission_repo)]
TheatreRepoDep = Annotated[TheatreRepository, Depends(get_theatre_repo)]
MovieRepoDep = Annotated[MovieRepository, Depends(get_movie_repo)]
LayoutRepoDep = Annotated[LayoutRepository, Depends(get_layout_repo)]
ScreenRepoDep = Annotated[ScreenRepository, Depends(get_screen_repo)]
ShowRepoDep = Annotated[ShowRepository, Depends(get_show_repo)]


def get_auth_service(
    redis: RedisDep, user_repo: UserRepoDep, email_service: EmailServiceDep
) -> AuthService:
    return AuthService(redis=redis, user_repo=user_repo, email_service=email_service)


def get_admin_service(
    db: DBDep,
    redis: RedisDep,
    user_repo: UserRepoDep,
    theatre_repo: TheatreRepoDep,
    movie_repo: MovieRepoDep,
) -> AdminService:
    return AdminService(
        db=db,
        redis=redis,
        user_repo=user_repo,
        theatre_repo=theatre_repo,
        movie_repo=movie_repo,
    )


def get_theatre_admin_service(db: DBDep, redis: RedisDep, layout_repo: LayoutRepoDep, screen_repo: ScreenRepoDep, theatre_repo: TheatreRepoDep, movie_repo: MovieRepoDep, show_repo: ShowRepoDep) -> TheatreAdminService:
    return TheatreAdminService(
        db=db,
        redis=redis,
        layout_repo=layout_repo,
        screen_repo=screen_repo,
        theatre_repo=theatre_repo,
        movie_repo=movie_repo,
        show_repo=show_repo
    )


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
AdminServiceDep = Annotated[AdminService, Depends(get_admin_service)]
TheatreAdminServiceDep = Annotated[
    TheatreAdminService, Depends(get_theatre_admin_service)
]


def get_current_user(authorization: Annotated[str, Header(...)]) -> str:
    return get_user_id(authorization=authorization)


def permission_required(permission: str):

    async def permission_dependency(
        authorization: Annotated[str, Header(...)],
        db: DBDep,
        permission_repo: PermissionRepoDep,
    ):
        user_id = get_user_id(authorization=authorization)

        async with db.begin():
            permission_repo.db = db
            is_allowed = await permission_repo.permission_check_repo(
                user_id=user_id, permission=permission
            )

        if not is_allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission",
            )

        return None

    return permission_dependency


def get_user_id(authorization: str) -> str:
    if authorization.startswith("Bearer "):
        token = authorization.split(" ")[1]

        payload = decode_token(token=token, secret=settings.JWT_SECRET_ACCESS_KEY)

        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Token not found"
            )

        user = payload.get("sub")
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="User id not found"
            )

        return user
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST, detail="Token is invalid"
    )


GetUserDep = Annotated[str, Depends(get_current_user)]
