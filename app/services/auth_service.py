from app.schemas.standard_schema import ResponseSchema
import requests
from fastapi import Response, HTTPException
from fastapi.responses import RedirectResponse
from app.utils.helper import (
    send_email,
    validate_otp,
    generate_access_token_and_refresh_token,
)

from urllib.parse import urlencode
from app.core.redis_config import Redis
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.user_repository import UserRepository

from app.utils.helper import generate_otp
from app.core.config import settings
from app.schemas.standard_schema import create_response

GOOGLE_CLIENT_ID = settings.GOOGLE_CLIENT_ID
GOOGLE_CLIENT_SECRET = settings.GOOGLE_CLIENT_SECRET
GOOGLE_REDIRECT_URI = settings.GOOGLE_REDIRECT_URI

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"


class AuthService:

    def __init__(self, redis: Redis, user_repo: UserRepository):
        self.redis = redis
        self.user_repo = user_repo

    async def auth_send_otp_service(self, email: str) -> ResponseSchema:
        otp = await generate_otp()

        # Use self.redis
        await self.redis.hsetex(name=email, mapping={"otp": otp, "tries": 3}, ex=600)

        send_email(
            email_content={
                "receiver_email": email,
                "subject": "Signin OTP - Online Ticket Booking System",
                "body": f"""
                <html>
                    <body>
                        <h1>Verify Your Account</h1>
                        <p>Thank you for registering. Please use the following One-Time Password (OTP) to complete your signup:</p>
                        <h2 style="color: #4CAF50;">{otp}</h2>
                        <p>This code is valid for 10 minutes.</p>
                    </body>
                </html>
            """,
            }
        )
        return create_response(message="OTP sent to your email")

    async def auth_signin_service(
        self,
        user_signin_body: dict,
        db: AsyncSession,
        response: Response,
    ) -> ResponseSchema:
        user_email = user_signin_body.get("email")
        user_otp = user_signin_body.get("otp")

        is_otp_validated = await validate_otp(
            email=user_email, otp=user_otp, redis=self.redis
        )

        if is_otp_validated:
            async with db.begin():
                user_found = await self.user_repo.get_user_by_email_repo(
                    email=user_email
                )

                if user_found:
                    await generate_access_token_and_refresh_token(
                        payload={"user_id": str(user_found.id)}, response=response
                    )
                    return create_response(message="User login successfully")
                else:
                    new_user = await self.user_repo.create_new_user_repo(
                        email=user_email
                    )
                    await generate_access_token_and_refresh_token(
                        payload={"user_id": str(new_user.id)}, response=response
                    )
                    return create_response(message="User created successfully")

    async def auth_login_google_service(self):
        params = {
            "client_id": GOOGLE_CLIENT_ID,
            "redirect_uri": GOOGLE_REDIRECT_URI,
            "response_type": "code",
            "scope": "openid email profile",
            "access_type": "offline",
            "prompt": "consent",
        }
        url = f"{GOOGLE_AUTH_URL}?{urlencode(params)}"
        return RedirectResponse(url=url)

    async def auth_google_callback_service(
        self, code: str, db: AsyncSession, response: Response
    ):
        token_data = {
            "code": code,
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "redirect_uri": GOOGLE_REDIRECT_URI,
            "grant_type": "authorization_code",
        }

        token_response = requests.post(GOOGLE_TOKEN_URL, data=token_data)
        token_json = token_response.json()

        if "error" in token_json:
            raise HTTPException(
                status_code=400, detail=token_json.get("error_description")
            )

        access_token = token_json.get("access_token")
        user_info_response = requests.get(
            GOOGLE_USERINFO_URL, headers={"Authorization": f"Bearer {access_token}"}
        )
        user_info = user_info_response.json()
        email = user_info.get("email")

        async with db.begin():
            user = await self.user_repo.get_user_by_email_repo(email=email)
            if not user:
                user = await self.user_repo.create_new_user_repo(email=email)

            await generate_access_token_and_refresh_token(
                payload={"user_id": str(user.id)}, response=response
            )

        return create_response(data={"email": user.email}, message="Login successful")
