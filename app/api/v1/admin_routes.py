from fastapi import APIRouter, status, Depends
from app.api.dependencies import AdminServiceDep, permission_required

from app.schemas.admin_schema import CreateUserSchema
from app.schemas.standard_schema import ResponseSchema


admin_router = APIRouter(prefix="/admin", tags=["admin"])


@admin_router.post(
    "/create-user",
    status_code=status.HTTP_201_CREATED,
    response_model=ResponseSchema,
    dependencies=[Depends(permission_required("admin:create-user"))]
)
async def create_user_route(
    user_body: CreateUserSchema,
    admin_service: AdminServiceDep
):
    return await admin_service.create_user_service(user_body=user_body.model_dump())
