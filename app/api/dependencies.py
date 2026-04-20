from typing import Annotated
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends, HTTPException, Header, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from app.core.redis_config import get_redis, Redis
from app.db.session import get_db
from app.utils.helper import decode_token
from app.core.config import settings

# Service Imports
from app.services.auth_service import AuthService
from app.services.admin_service import AdminService
from app.services.theatre_admin_service import TheatreAdminService
from app.services.email_service import EmailService
from app.services.user_service import UserService
from app.services.seat_layout_service import SeatLayoutService

# Repository Imports
from app.repositories.user_repository import UserRepository
from app.repositories.permission_repository import PermissionRepo
from app.repositories.theatre_repository import TheatreRepository
from app.repositories.movie_repository import MovieRepository
from app.repositories.layout_repository import LayoutRepository
from app.repositories.screen_repository import ScreenRepository
from app.repositories.show_repository import ShowRepository
from app.repositories.booking_repository import BookingRepository
from app.repositories.booked_ticket_repository import BookingTicketRepository

DBDep = Annotated[AsyncSession, Depends(get_db)]
RedisDep = Annotated[Redis, Depends(get_redis)]


# --- REPOSITORY FACTORIES ---
def get_repo(repo_class):
    """Return repository instance with database dependency."""

    def _get_repo(db: DBDep):
        return repo_class(db=db)

    return _get_repo


UserRepoDep = Annotated[UserRepository, Depends(get_repo(UserRepository))]
PermissionRepoDep = Annotated[PermissionRepo, Depends(get_repo(PermissionRepo))]
TheatreRepoDep = Annotated[TheatreRepository, Depends(get_repo(TheatreRepository))]
MovieRepoDep = Annotated[MovieRepository, Depends(get_repo(MovieRepository))]
LayoutRepoDep = Annotated[LayoutRepository, Depends(get_repo(LayoutRepository))]
ScreenRepoDep = Annotated[ScreenRepository, Depends(get_repo(ScreenRepository))]
ShowRepoDep = Annotated[ShowRepository, Depends(get_repo(ShowRepository))]
BookingRepoDep = Annotated[BookingRepository, Depends(get_repo(BookingRepository))]
BookingTicketRepositoryDep = Annotated[BookingTicketRepository, Depends(get_repo(BookingTicketRepository))]


# --- SERVICE FACTORIES ---
def get_email_service() -> EmailService:
    """Create email service instance."""
    return EmailService()


EmailServiceDep = Annotated[EmailService, Depends(get_email_service)]


def get_auth_service(
    redis: RedisDep, user_repo: UserRepoDep, email_service: EmailServiceDep
) -> AuthService:
    """Create auth service with required dependencies."""
    return AuthService(redis=redis, user_repo=user_repo, email_service=email_service)


def get_admin_service(
    db: DBDep,
    redis: RedisDep,
    user_repo: UserRepoDep,
    theatre_repo: TheatreRepoDep,
    movie_repo: MovieRepoDep,
) -> AdminService:
    """Create admin service with required dependencies."""
    return AdminService(
        db=db,
        redis=redis,
        user_repo=user_repo,
        theatre_repo=theatre_repo,
        movie_repo=movie_repo,
    )


def get_user_service(
    db: DBDep,
    redis: RedisDep,
    movie_repo: MovieRepoDep,
    theatre_repo: TheatreRepoDep,
    show_repo: ShowRepoDep,
    booking_repo: BookingRepoDep,
    user_repo: UserRepoDep,
    booked_ticket_repo: BookingTicketRepositoryDep,
    email_service: EmailServiceDep
) -> UserService:
    """Create user service with required dependencies."""
    return UserService(
        db=db,
        redis=redis,
        movie_repo=movie_repo,
        theatre_repo=theatre_repo,
        show_repo=show_repo,
        booking_repo=booking_repo,
        user_repo=user_repo,
        booked_ticket_repo=booked_ticket_repo,
        email_service=email_service
    )


def get_theatre_admin_service(
    db: DBDep,
    redis: RedisDep,
    layout_repo: LayoutRepoDep,
    screen_repo: ScreenRepoDep,
    theatre_repo: TheatreRepoDep,
    movie_repo: MovieRepoDep,
    show_repo: ShowRepoDep,
    booked_ticket_repo: BookingTicketRepositoryDep,
) -> TheatreAdminService:
    """Create theatre admin service with required dependencies."""
    return TheatreAdminService(
        db=db,
        redis=redis,
        layout_repo=layout_repo,
        screen_repo=screen_repo,
        theatre_repo=theatre_repo,
        movie_repo=movie_repo,
        show_repo=show_repo,
        booked_ticket_repo=booked_ticket_repo
    )


def get_seat_layout_service(db: DBDep, redis: RedisDep) -> SeatLayoutService:
    """Create seat layout service instance."""
    return SeatLayoutService(db=db, redis=redis)


# --- FINAL SERVICE DEPENDENCIES ---
AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
AdminServiceDep = Annotated[AdminService, Depends(get_admin_service)]
UserServiceDep = Annotated[UserService, Depends(get_user_service)]
TheatreAdminServiceDep = Annotated[
    TheatreAdminService, Depends(get_theatre_admin_service)
]
SeatLayoutServiceDep = Annotated[SeatLayoutService, Depends(get_seat_layout_service)]

security = HTTPBearer()


# --- AUTHENTICATION HELPERS ---
async def get_user_id(
    token_data: Annotated[HTTPAuthorizationCredentials, Depends(security)],
) -> str:
    """Extract user ID from access token using HTTPBearer."""
    token = token_data.credentials

    payload = decode_token(token=token, secret=settings.JWT_SECRET_ACCESS_KEY)

    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token"
        )

    return payload["sub"]


GetUserDep = Annotated[str, Depends(get_user_id)]


def permission_required(permission: str):
    """Check if user has required permission."""

    async def permission_dependency(
        user_id: GetUserDep,
        db: DBDep,
        permission_repo: PermissionRepoDep,
    ):
        async with db.begin():
            permission_repo.db = db
            if not await permission_repo.permission_check_repo(
                user_id=user_id, permission=permission
            ):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied"
                )

    return permission_dependency
