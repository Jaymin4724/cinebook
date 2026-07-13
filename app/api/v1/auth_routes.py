from fastapi import APIRouter, status, Body, Response, BackgroundTasks
from typing import Annotated
from fastapi.responses import RedirectResponse
from pydantic import EmailStr

from app.api.dependencies import DBDep, AuthServiceDep, AccessTokenPayloadDep
from app.schemas.standard_schema import ResponseSchema
from app.schemas.user_schema import UserSigninSchema, RefreshTokenSchema, LogoutSchema

auth_router = APIRouter(prefix="/auth", tags=["auth"])
google_auth_router = APIRouter(prefix="/auth/google", tags=["google auth"])


@auth_router.post(
    "/send-otp", status_code=status.HTTP_200_OK, response_model=ResponseSchema
)
async def auth_send_otp_route(
    email: Annotated[EmailStr, Body(embed=True)],
    auth_service: AuthServiceDep,
    background_tasks: BackgroundTasks,
):
    """Send an OTP to the given email for login."""
    return await auth_service.auth_send_otp_service(
        email=email, background_tasks=background_tasks
    )


@auth_router.post(
    "/signin", status_code=status.HTTP_201_CREATED, response_model=ResponseSchema
)
async def auth_signin_route(
    user_signin_body: Annotated[UserSigninSchema, Body(...)],
    db: DBDep,
    response: Response,
    auth_service: AuthServiceDep,
):
    """Verify OTP and sign in the user."""
    return await auth_service.auth_signin_service(
        user_signin_body=user_signin_body.model_dump(),
        db=db,
        response=response,
    )


@auth_router.post(
    "/refresh", status_code=status.HTTP_201_CREATED, response_model=ResponseSchema
)
async def auth_refresh_route(
    refresh_body: Annotated[RefreshTokenSchema, Body(...)],
    response: Response,
    auth_service: AuthServiceDep,
):
    """Issue a new access/refresh token pair from a valid refresh token."""
    return await auth_service.auth_refresh_service(
        refresh_token=refresh_body.refresh_token,
        response=response,
    )


@auth_router.post(
    "/logout", status_code=status.HTTP_200_OK, response_model=ResponseSchema
)
async def auth_logout_route(
    access_payload: AccessTokenPayloadDep,
    logout_body: Annotated[LogoutSchema, Body(...)],
    auth_service: AuthServiceDep,
):
    """Revoke the current access token, and the refresh token if provided."""
    return await auth_service.auth_logout_service(
        access_payload=access_payload,
        refresh_token=logout_body.refresh_token,
    )


@google_auth_router.get("/login", response_class=RedirectResponse)
async def auth_login_google(
    auth_service: AuthServiceDep,
):
    """Redirect user to Google login page."""
    return await auth_service.auth_login_google_service()


@google_auth_router.get(
    "/callback", status_code=status.HTTP_200_OK, response_model=ResponseSchema
)
async def auth_google_callback(
    code: str,
    state: str,
    db: DBDep,
    response: Response,
    auth_service: AuthServiceDep,
):
    """Handle Google login callback and authenticate user."""
    return await auth_service.auth_google_callback_service(
        code=code, state=state, db=db, response=response
    )
