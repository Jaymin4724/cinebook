from fastapi import APIRouter, status, Depends, Body
from app.api.dependencies import permission_required

from app.schemas.standard_schema import ResponseSchema
from app.schemas.layout_schema import CreateLayoutSchema
from app.schemas.screen_schema import CreateScreenSchema

from app.api.dependencies import TheatreAdminServiceDep, get_current_user

from typing import Annotated

theatre_admin_router = APIRouter(prefix="/theatre-admin", tags=["theatre admin"])

@theatre_admin_router.post(
    "/create-layout",
    status_code=status.HTTP_201_CREATED,
    response_model=ResponseSchema,
    dependencies=[Depends(permission_required("create-layout"))]
)
async def create_layout_route(
    layout_body: Annotated[CreateLayoutSchema, Body(...)],
    theatre_admin_service: TheatreAdminServiceDep,
    user_id: Annotated[str, Depends(get_current_user)]
):
    return await theatre_admin_service.create_layout_service(
        layout_body=layout_body.model_dump(),
        user_id=user_id
    )


@theatre_admin_router.post(
    "/create-screen",
    status_code=status.HTTP_201_CREATED,
    response_model=ResponseSchema,
    dependencies=[Depends(permission_required("create-screen"))]
)
async def create_screen_route(
    screen_body: Annotated[CreateScreenSchema, Body(...)],
    theatre_admin_service: TheatreAdminServiceDep,
    user_id: Annotated[str, Depends(get_current_user)]
):
    return await theatre_admin_service.create_screen_service(
        screen_body=screen_body.model_dump(),
        user_id=user_id
    )