from fastapi import APIRouter, status, Depends, Body, Query
from app.api.dependencies import AdminServiceDep, permission_required

from app.schemas.user_schema import CreateUserSchema
from app.schemas.standard_schema import ResponseSchema
from app.schemas.theatre_schema import CreateTheatreSchema
from app.schemas.pagination_schema import PaginationSchema

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
    return await admin_service.create_user_service(user_body=user_body.model_dump())


@admin_router.post(
    "/create-theatre",
    status_code=status.HTTP_201_CREATED,
    response_model=ResponseSchema,
    dependencies=[Depends(permission_required("create-theatre"))],
)
async def create_theatre_router(
    theatre_body: CreateTheatreSchema, admin_service: AdminServiceDep
):
    return await admin_service.create_theatre_service(
        theatre_body=theatre_body.model_dump()
    )


@admin_router.post(
    "/create-movie",
    status_code=status.HTTP_201_CREATED,
    response_model=ResponseSchema,
    dependencies=[Depends(permission_required("create-movie"))],
)
async def create_movie_router(
    imdb_id: Annotated[str, Body(embed=True)], admin_service: AdminServiceDep
):
    return await admin_service.create_new_movie_service(imdb_id=imdb_id)

@admin_router.get(
    "/users",
    status_code=status.HTTP_200_OK,
    response_model=ResponseSchema,
    dependencies=[Depends(permission_required("read-users"))],
)
async def get_all_users_router(
    admin_service: AdminServiceDep, pagination: Annotated[PaginationSchema, Query()]
):
    return await admin_service.get_all_users_service(
        page=pagination.page, size=pagination.size
    )


@admin_router.get(
    "/theatres",
    status_code=status.HTTP_200_OK,
    response_model=ResponseSchema,
    dependencies=[Depends(permission_required("read-theatres"))],
)
async def get_all_theatres_router(
    admin_service: AdminServiceDep, pagination: Annotated[PaginationSchema, Query()]
):
    return await admin_service.get_all_theatres_service(
        page=pagination.page, size=pagination.size
    )


@admin_router.get(
    "/movies",
    status_code=status.HTTP_200_OK,
    response_model=ResponseSchema,
    dependencies=[Depends(permission_required("read-movies"))],
)
async def get_all_movies_router(
    admin_service: AdminServiceDep, pagination: Annotated[PaginationSchema, Query()]
):
    return await admin_service.get_all_movies_service(
        page=pagination.page, size=pagination.size
    )
