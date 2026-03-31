from fastapi import APIRouter, status, Body, Response
from typing import Annotated
from pydantic import EmailStr

from app.api.dependencies import DBDep, RedisDep, AuthServiceDep, UserRepoDep

from app.schemas.standard_schema import ResponseSchema
from app.schemas.user_schema import UserSigninSchema

auth_router = APIRouter(prefix="/auth", tags=["auth"])
google_auth_router = APIRouter(prefix="/google", tags=["auth"])

@auth_router.post(
    "/send-otp", status_code=status.HTTP_200_OK, response_model=ResponseSchema
)
async def auth_send_otp_route(
    email: Annotated[EmailStr, Body(embed=True)],
    redis: RedisDep,
    auth_service: AuthServiceDep,
):
    return await auth_service.auth_send_otp_service(email=email, redis=redis)


@auth_router.post(
    "/signin", status_code=status.HTTP_201_CREATED, response_model=ResponseSchema
)
async def auth_signin_route(
    user_signin_body: Annotated[UserSigninSchema, Body(...)],
    db: DBDep,
    redis: RedisDep,
    response: Response,
    auth_service: AuthServiceDep,
    user_repo: UserRepoDep,
):
    return await auth_service.auth_signin_service(
        user_signin_body=user_signin_body.model_dump(),
        redis=redis,
        db=db,
        response=response,
        user_repo=user_repo,
    )


@google_auth_router.get(
    "/login", status_code=status.HTTP_200_OK, response_model=ResponseSchema
)
async def auth_login_google(
    auth_service: AuthServiceDep,
):
    return await auth_service.auth_login_google_service()


@google_auth_router.get(
    "/callback", status_code=status.HTTP_200_OK, response_model=ResponseSchema
)
async def auth_google_callback(
    code: str,
    db: DBDep,
    response: Response,
    auth_service: AuthServiceDep,
    user_repo: UserRepoDep,
):
    return await auth_service.auth_google_callback_service(
        code=code, db=db, response=response, user_repo=user_repo
    )
