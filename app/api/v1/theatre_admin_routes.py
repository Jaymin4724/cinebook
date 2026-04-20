from fastapi import APIRouter, status, Depends, Body, Query
from app.api.dependencies import permission_required

from app.schemas.standard_schema import ResponseSchema
from app.schemas.layout_schema import CreateLayoutSchema
from app.schemas.screen_schema import CreateScreenSchema
from app.schemas.show_schema import CreateShowSchema
from app.schemas.pagination_schema import PaginationSchema

from app.api.dependencies import TheatreAdminServiceDep, GetUserDep

from typing import Annotated

theatre_admin_router = APIRouter(prefix="/theatre-admin", tags=["theatre admin"])


@theatre_admin_router.post(
    "/create-layout",
    status_code=status.HTTP_201_CREATED,
    response_model=ResponseSchema,
    dependencies=[Depends(permission_required("create-layout"))],
)
async def create_layout_route(
    layout_body: Annotated[CreateLayoutSchema, Body(...)],
    theatre_admin_service: TheatreAdminServiceDep,
    user_id: GetUserDep,
):
    """Create a new seat layout for a theatre."""
    return await theatre_admin_service.create_layout_service(
        layout_body=layout_body.model_dump(), user_id=user_id
    )


@theatre_admin_router.post(
    "/create-screen",
    status_code=status.HTTP_201_CREATED,
    response_model=ResponseSchema,
    dependencies=[Depends(permission_required("create-screen"))],
)
async def create_screen_route(
    screen_body: Annotated[CreateScreenSchema, Body(...)],
    theatre_admin_service: TheatreAdminServiceDep,
    user_id: GetUserDep,
):
    """Create a new screen in a theatre."""
    return await theatre_admin_service.create_screen_service(
        screen_body=screen_body.model_dump(), user_id=user_id
    )


@theatre_admin_router.post(
    "/create-show",
    status_code=status.HTTP_201_CREATED,
    response_model=ResponseSchema,
    dependencies=[Depends(permission_required("create-show"))],
)
async def create_show_route(
    show_body: Annotated[CreateShowSchema, Body(...)],
    theatre_admin_service: TheatreAdminServiceDep,
    user_id: GetUserDep,
):
    """Create a new show for a screen."""
    return await theatre_admin_service.create_show_service(
        show_body=show_body.model_dump(), user_id=user_id
    )


@theatre_admin_router.get(
    "/my-theatres",
    status_code=status.HTTP_200_OK,
    response_model=ResponseSchema,
    dependencies=[Depends(permission_required("read-my-theatres"))],
)
async def get_my_theatres_route(
    theatre_admin_service: TheatreAdminServiceDep,
    user_id: GetUserDep,
    pagination: Annotated[PaginationSchema, Query()],
):
    """Fetch all theatres for logged-in theatre admin."""
    return await theatre_admin_service.get_my_theatres_service(
        user_id=user_id, page=pagination.page, size=pagination.size
    )


@theatre_admin_router.get(
    "/my-screens",
    status_code=status.HTTP_200_OK,
    response_model=ResponseSchema,
    dependencies=[Depends(permission_required("read-my-screens"))],
)
async def get_my_screens_route(
    theatre_admin_service: TheatreAdminServiceDep,
    user_id: GetUserDep,
    pagination: Annotated[PaginationSchema, Query()],
):
    """Fetch all screens for logged-in theatre admin."""
    return await theatre_admin_service.get_my_screens_service(
        user_id=user_id, page=pagination.page, size=pagination.size
    )


@theatre_admin_router.delete(
    "/screen/delete/{screen_id}",
    status_code=status.HTTP_200_OK,
    response_model=ResponseSchema,
    dependencies=[Depends(permission_required("delete-screen"))],
)
async def delete_screen_route(
    screen_id: str, user_id: GetUserDep, theatre_admin_service: TheatreAdminServiceDep
):
    """Delete screen by ID."""
    return await theatre_admin_service.delete_screen_service(
        screen_id=screen_id, user_id=user_id
    )


@theatre_admin_router.delete(
    "/show/delete/{show_id}",
    status_code=status.HTTP_200_OK,
    response_model=ResponseSchema,
    dependencies=[Depends(permission_required("delete-show"))],
)
async def delete_show_route(
    show_id: str, user_id: GetUserDep, theatre_admin_service: TheatreAdminServiceDep
):
    """Delete show by ID."""
    return await theatre_admin_service.delete_show_service(
        show_id=show_id, user_id=user_id
    )


@theatre_admin_router.post(
    "/verify-ticket",
    status_code=status.HTTP_200_OK,
    response_model=ResponseSchema,
    dependencies=[Depends(permission_required("verify-ticket"))]
)
async def verify_ticket_route(
    ticket_hash: Annotated[str,Body(embed=True)],
    user_id: GetUserDep,
    theatre_admin_service: TheatreAdminServiceDep
):
    return await theatre_admin_service.verify_ticket_service(
        ticket_hash=ticket_hash,
        user_id=user_id
    )