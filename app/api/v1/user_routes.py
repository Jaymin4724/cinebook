from fastapi import APIRouter, status, Query, Body
from typing import Annotated
from app.api.dependencies import UserServiceDep, SeatLayoutServiceDep, GetUserDep
from app.schemas.standard_schema import ResponseSchema
from app.schemas.pagination_schema import PaginationSchema

user_router = APIRouter(prefix="/users", tags=["users"])


@user_router.get(
    "/theatre/{theatre_id}/movies",
    status_code=status.HTTP_200_OK,
    response_model=ResponseSchema,
)
async def get_movies_by_theatre(
    theatre_id: str,
    user_service: UserServiceDep,
    pagination: Annotated[PaginationSchema, Query()],
):
    """Fetch movies running in a theatre."""
    return await user_service.get_movies_by_theatre_service(
        theatre_id=theatre_id, page=pagination.page, size=pagination.size
    )


@user_router.get(
    "/movie/{movie_id}/theatres",
    status_code=status.HTTP_200_OK,
    response_model=ResponseSchema,
)
async def get_theatres_by_movie(
    movie_id: str,
    user_service: UserServiceDep,
    pagination: Annotated[PaginationSchema, Query()],
):
    """Fetch theatres showing a movie."""
    return await user_service.get_theatres_by_movie_service(
        movie_id=movie_id, page=pagination.page, size=pagination.size
    )


@user_router.get(
    "/theatre/{theatre_id}/movie/{movie_id}",
    status_code=status.HTTP_200_OK,
    response_model=ResponseSchema,
)
@user_router.get(
    "/movie/{movie_id}/theatre/{theatre_id}",
    status_code=status.HTTP_200_OK,
    response_model=ResponseSchema,
)
async def get_shows(
    theatre_id: str,
    movie_id: str,
    user_service: UserServiceDep,
    pagination: Annotated[PaginationSchema, Query()],
):
    """Fetch shows for a movie in a theatre."""
    return await user_service.get_shows_service(
        theatre_id=theatre_id,
        movie_id=movie_id,
        page=pagination.page,
        size=pagination.size,
    )


@user_router.get(
    "/show/{show_id}",
    status_code=status.HTTP_200_OK,
    response_model=ResponseSchema,
)
async def get_show_by_id(
    show_id: str,
    user_service: UserServiceDep,
    seat_layout_service: SeatLayoutServiceDep,
):
    """Fetch show details with seat layout."""
    return await user_service.get_show_details_service(
        show_id=show_id, seat_layout_service=seat_layout_service
    )


@user_router.post(
    "/show/{show_id}/seat-lock",
    status_code=status.HTTP_201_CREATED,
    response_model=ResponseSchema,
)
async def lock_seat_route(
    show_id: str,
    user_id: GetUserDep,
    seat_array: Annotated[list[str], Body(embed=True)],
    user_service: UserServiceDep,
    seat_layout_service: SeatLayoutServiceDep,
):
    """Lock selected seats for a show."""
    return await user_service.lock_seat_service(
        show_id=show_id,
        user_id=user_id,
        seat_array=seat_array,
        seat_layout_service=seat_layout_service,
    )


@user_router.post(
    "/show/{show_id}/seat-book",
    status_code=status.HTTP_201_CREATED,
    response_model=ResponseSchema,
)
async def book_tickets(
    show_id: str,
    user_id: GetUserDep,
    seat_array: Annotated[list[str], Body(embed=True)],
    user_service: UserServiceDep,
):
    """Book selected seats for a show."""
    return await user_service.book_ticket_service(
        show_id=show_id, user_id=user_id, seat_array=seat_array
    )


@user_router.delete(
    "/user/delete", status_code=status.HTTP_200_OK, response_model=ResponseSchema
)
async def delete_user_router(user_id: GetUserDep, user_service: UserServiceDep):
    """Delete current user account."""
    return await user_service.delete_user_service(user_id=user_id)
