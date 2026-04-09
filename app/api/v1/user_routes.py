from fastapi import APIRouter, status, Query
from typing import Annotated
from app.api.dependencies import UserServiceDep
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
async def get_show_by_id(show_id: str, user_service: UserServiceDep):
    return await user_service.get_show_details_service(show_id=show_id)
