from app.schemas.standard_schema import ResponseSchema
import httpx
import secrets
from fastapi import Response, HTTPException, status, BackgroundTasks
from fastapi.responses import RedirectResponse
from urllib.parse import urlencode
from sqlalchemy.ext.asyncio import AsyncSession

from app.utils.helper import (
    validate_otp,
    generate_access_token_and_refresh_token,
    generate_otp,
    decode_token,
    blacklist_token,
    is_token_revoked,
)

from app.services.email_service import EmailService
from app.core.redis_config import Redis
from app.repositories.user_repository import UserRepository
from app.core.config import settings
from app.schemas.standard_schema import create_response

GOOGLE_CLIENT_ID = settings.GOOGLE_CLIENT_ID
GOOGLE_CLIENT_SECRET = settings.GOOGLE_CLIENT_SECRET
GOOGLE_REDIRECT_URI = settings.GOOGLE_REDIRECT_URI

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"


class AuthService:
    """Handle authentication related operations."""

    def __init__(
        self, redis: Redis, user_repo: UserRepository, email_service: EmailService
    ):

        self.redis = redis
        self.user_repo = user_repo
        self.email_service = email_service

    async def auth_send_otp_service(
        self, email: str, background_tasks: BackgroundTasks
    ) -> ResponseSchema:
        """Generate OTP, store it, and send it to user email."""
        otp = generate_otp()

        await self.redis.hset(name=email, mapping={"otp": otp, "tries": 3})
        await self.redis.expire(email, 600)

        background_tasks.add_task(
            self.email_service.send_otp_email, email_to=email, otp=otp
        )

        return create_response(data={"email": email},message="OTP sent to your email")

    async def auth_signin_service(
        self,
        user_signin_body: dict,
        db: AsyncSession,
        response: Response,
    ) -> ResponseSchema:
        """Verify OTP and log in or create the user."""
        user_email = user_signin_body.get("email")
        user_otp = user_signin_body.get("otp")
        self.user_repo.db = db

        await validate_otp(email=user_email, otp=user_otp, redis=self.redis)

        async with db.begin():
            user_found = await self.user_repo.get_user_by_email_repo(email=user_email)

            if user_found:
                if user_found.is_active == False:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="User account is deleted",
                    )
                tokens = generate_access_token_and_refresh_token(
                    payload={"user_id": str(user_found.id)}, response=response
                )
                return create_response(data=tokens, message="User login successfully")
            else:
                new_user = await self.user_repo.create_new_user_repo(email=user_email)
                tokens = generate_access_token_and_refresh_token(
                    payload={"user_id": str(new_user.id)}, response=response
                )
                return create_response(data=tokens, message="User created successfully")

    async def auth_refresh_service(
        self, refresh_token: str, response: Response
    ) -> ResponseSchema:
        """Issue a new access/refresh token pair from a valid refresh token."""
        payload = decode_token(
            token=refresh_token,
            secret=settings.JWT_SECRET_REFRESH_KEY,
            expected_type="refresh",
        )

        if not payload or "sub" not in payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token",
            )

        if await is_token_revoked(redis=self.redis, jti=payload.get("jti")):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token has been revoked",
            )

        await blacklist_token(
            redis=self.redis, jti=payload["jti"], exp=payload["exp"]
        )

        tokens = generate_access_token_and_refresh_token(
            payload={"user_id": payload["sub"]}, response=response
        )
        return create_response(data=tokens, message="Token refreshed successfully")

    async def auth_logout_service(
        self, access_payload: dict, refresh_token: str | None
    ) -> ResponseSchema:
        """Revoke the current access token, and the refresh token if provided."""
        await blacklist_token(
            redis=self.redis, jti=access_payload["jti"], exp=access_payload["exp"]
        )

        if refresh_token:
            refresh_payload = decode_token(
                token=refresh_token,
                secret=settings.JWT_SECRET_REFRESH_KEY,
                expected_type="refresh",
            )
            if refresh_payload:
                await blacklist_token(
                    redis=self.redis,
                    jti=refresh_payload["jti"],
                    exp=refresh_payload["exp"],
                )

        return create_response(message="Logged out successfully")

    async def auth_login_google_service(self):
        """Generate Google OAuth URL with a CSRF state and redirect user."""
        state = secrets.token_urlsafe(32)
        await self.redis.set(f"oauth_state_{state}", "1", ex=600)

        params = {
            "client_id": GOOGLE_CLIENT_ID,
            "redirect_uri": GOOGLE_REDIRECT_URI,
            "response_type": "code",
            "scope": "openid email profile",
            "access_type": "offline",
            "prompt": "consent",
            "state": state,
        }
        url = f"{GOOGLE_AUTH_URL}?{urlencode(params)}"
        return RedirectResponse(url=url)

    async def auth_google_callback_service(
        self, code: str, state: str, db: AsyncSession, response: Response
    ):
        """Handle Google OAuth callback and log in the user."""
        # delete is atomic, so each state is single-use
        if not await self.redis.delete(f"oauth_state_{state}"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired OAuth state",
            )

        token_data = {
            "code": code,
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "redirect_uri": GOOGLE_REDIRECT_URI,
            "grant_type": "authorization_code",
        }

        async with httpx.AsyncClient() as client:
            token_response = await client.post(GOOGLE_TOKEN_URL, data=token_data)
            token_json = token_response.json()
            if token_response.status_code != 200 or "error" in token_json:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=token_json.get("error_description"),
                )

            access_token = token_json.get("access_token")
            user_info_response = await client.get(
                GOOGLE_USERINFO_URL, headers={"Authorization": f"Bearer {access_token}"}
            )
            user_info = user_info_response.json()
            email = user_info.get("email")
            google_id = user_info.get("sub")
            first_name = user_info.get("given_name", None)
            last_name = user_info.get("family_name", None)

        self.user_repo.db = db

        async with db.begin():
            user = await self.user_repo.get_user_by_email_repo(email=email)
            if not user:
                user = await self.user_repo.create_new_user_repo(
                    email=email,
                    google_id=google_id,
                    first_name=first_name,
                    last_name=last_name,
                )
            if user.is_active == False:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="User account is deleted",
                )
            elif not user.google_id:
                user.google_id = google_id
                if user.user_detail:
                    user.user_detail.first_name = (
                        user.user_detail.first_name or first_name
                    )
                    user.user_detail.last_name = user.user_detail.last_name or last_name

            tokens = generate_access_token_and_refresh_token(
                payload={"user_id": str(user.id)}, response=response
            )

        return create_response(
            data={"email": user.email, **tokens}, message="Login successful"
        )
