from app.core.redis_config import Redis
from app.schemas.standard_schema import ResponseSchema
from app.utils.helper import generate_otp
from fastapi import BackgroundTasks, HTTPException, status, Response
from app.utils.helper import send_email, validate_otp, encode_jwt, generate_access_token_and_refresh_token
from app.schemas.standard_schema import create_response
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta

from app.repositories.user_repository import UserRepository
from app.core.config import settings


class AuthServices:
    
    async def auth_send_otp_service(self, email: str, redis: Redis) -> ResponseSchema:

        otp = await generate_otp()

        await redis.hsetex(
            name=email,
            mapping={
                "otp": otp,
                "tries": 3
            },
            ex=600
        )

        send_email(email_content={
            "receiver_email" : email,
            "subject" : "Signin OTP - Online Ticket Booking System",
            "body" : f"""
                <html>
                    <body>
                        <h1>Verify Your Account</h1>
                        <p>Thank you for registering. Please use the following One-Time Password (OTP) to complete your signup:</p>
                        <h2 style="color: #4CAF50;">{otp}</h2>
                        <p>This code is valid for 10 minutes. If you did not request this, please ignore this email.</p>
                    </body>
                </html>
            """
        })

        return create_response(message="OTP sent to your email")
    

    async def auth_signin_service(self, user_signin_body: dict, redis: Redis, db: AsyncSession, response: Response) -> ResponseSchema:
        
        user_email = user_signin_body.get("email")
        user_otp = user_signin_body.get("otp")

        is_otp_validated = await validate_otp(
            email=user_email, 
            otp=user_otp, 
            redis=redis
        )

        if is_otp_validated:

            async with db.begin():
                user_found = await UserRepository().get_user_by_email_repo(
                    email=user_email,
                    db=db
                )

                if user_found:
                    await generate_access_token_and_refresh_token(
                        payload={
                            "user_id": str(user_found.id)
                        },
                        response=response
                    )
                    return create_response(message="User login successfully")
                else:
                    new_user = await UserRepository().create_new_user_repo(
                        email=user_email,
                        db=db
                    )
                    await generate_access_token_and_refresh_token(
                        payload={
                            "user_id": str(new_user.id)
                        },
                        response=response
                    )
                    return create_response(message="User created successfully")