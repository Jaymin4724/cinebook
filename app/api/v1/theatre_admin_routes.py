from fastapi import APIRouter, status, Depends, Body
from app.api.dependencies import permission_required

from app.schemas.standard_schema import ResponseSchema
from app.schemas.layout_schema import CreateLayoutSchema

from typing import Annotated

theatre_admin_router = APIRouter(prefix="/theatre_admin", tags=["theatre_admin"])

@theatre_admin_router.post(
    "/create-layout",
    status_code=status.HTTP_201_CREATED,
    response_model=ResponseSchema,
    dependencies=[Depends(permission_required("theatre_admin:create-screen"))]
)
async def create_layout_router(
    layout_body: Annotated[CreateLayoutSchema, Body(...)],
    
):
    pass