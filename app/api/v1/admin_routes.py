from fastapi import APIRouter, status, Depends, Body, Query
from app.api.dependencies import AdminServiceDep, permission_required

from app.schemas.user_schema import CreateUserSchema
from app.schemas.standard_schema import ResponseSchema
from app.schemas.theatre_schema import CreateTheatreSchema
from app.schemas.pagination_schema import PaginationSchema
from app.schemas.movie_schema import CreateMovieRequest

from typing import Annotated


admin_router = APIRouter(prefix="/admin", tags=["admin"])


@admin_router.post(
    "/create-user",
    status_code=status.HTTP_201_CREATED,
    response_model=ResponseSchema,
    dependencies=[Depends(permission_required("create-user"))],
)
async def create_user_route(
    user_body: CreateUserSchema, admin_service: AdminServiceDep
):
    """Create a new user with given details."""
    return await admin_service.create_user_service(user_body=user_body.model_dump())


@admin_router.post(
    "/create-theatre",
    status_code=status.HTTP_201_CREATED,
    response_model=ResponseSchema,
    dependencies=[Depends(permission_required("create-theatre"))],
)
async def create_theatre_route(
    theatre_body: CreateTheatreSchema, admin_service: AdminServiceDep
):
    """Create a new theatre."""
    return await admin_service.create_theatre_service(
        theatre_body=theatre_body.model_dump()
    )


@admin_router.post(
    "/create-movie",
    status_code=status.HTTP_201_CREATED,
    response_model=ResponseSchema,
    dependencies=[Depends(permission_required("create-movie"))],
)
async def create_movie_route(
    movie_payload: CreateMovieRequest, admin_service: AdminServiceDep
):
    """Create a new movie using IMDB ID."""
    return await admin_service.create_new_movie_service(movie_payload)


@admin_router.get(
    "/users",
    status_code=status.HTTP_200_OK,
    response_model=ResponseSchema,
    dependencies=[Depends(permission_required("read-users"))],
)
async def get_all_users_route(
    admin_service: AdminServiceDep, pagination: Annotated[PaginationSchema, Query()]
):
    """Fetch all users with pagination."""
    return await admin_service.get_all_users_service(
        page=pagination.page, size=pagination.size
    )


@admin_router.get(
    "/theatres",
    status_code=status.HTTP_200_OK,
    response_model=ResponseSchema,
    dependencies=[Depends(permission_required("read-theatres"))],
)
async def get_all_theatres_route(
    admin_service: AdminServiceDep, pagination: Annotated[PaginationSchema, Query()]
):
    """Fetch all theatres with pagination."""
    return await admin_service.get_all_theatres_service(
        page=pagination.page, size=pagination.size
    )


@admin_router.get(
    "/movies",
    status_code=status.HTTP_200_OK,
    response_model=ResponseSchema,
    dependencies=[Depends(permission_required("read-movies"))],
)
async def get_all_movies_route(
    admin_service: AdminServiceDep, pagination: Annotated[PaginationSchema, Query()]
):
    """Fetch all movies with pagination."""
    return await admin_service.get_all_movies_service(
        page=pagination.page, size=pagination.size
    )


@admin_router.delete(
    "/theatre/delete/{theatre_id}",
    status_code=status.HTTP_200_OK,
    response_model=ResponseSchema,
    dependencies=[Depends(permission_required("delete-theatre"))],
)
async def delete_theatre_router(theatre_id: str, admin_service: AdminServiceDep):
    """Delete theatre by ID."""
    return await admin_service.delete_theatre_service(theatre_id=theatre_id)


@admin_router.delete(
    "/movie/delete/{movie_id}",
    status_code=status.HTTP_200_OK,
    response_model=ResponseSchema,
    dependencies=[Depends(permission_required("delete-movie"))],
)
async def delete_movie_router(movie_id: str, admin_services: AdminServiceDep):
    """Delete movie by ID."""
    return await admin_services.delete_movie_service(movie_id=movie_id)
