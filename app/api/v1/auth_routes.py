from fastapi import APIRouter, status, Body, Response
from typing import Annotated
from pydantic import EmailStr

from app.api.dependencies import DBDep, REDISDep

from app.schemas.standard_schema import ResponseSchema
from app.schemas.user_schema import UserSigninSchema

from app.services.auth_services import AuthServices

auth_router = APIRouter(prefix='/auth', tags=['auth'])


@auth_router.post('/send-otp', status_code=status.HTTP_200_OK, response_model=ResponseSchema)
async def auth_send_otp_route(email: Annotated[EmailStr,Body(embed=True)], redis: REDISDep):
    return await AuthServices().auth_send_otp_service(email=email, redis=redis)


@auth_router.post('/signin', status_code=status.HTTP_201_CREATED, response_model=ResponseSchema)
async def auth_signin_route(user_signin_body: Annotated[UserSigninSchema, Body(...)], db: DBDep, redis: REDISDep, response: Response):
    return await AuthServices().auth_signin_service(user_signin_body=user_signin_body.model_dump(), redis=redis, db=db, response=response)