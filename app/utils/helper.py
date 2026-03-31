import random
import smtplib
import ssl
from email.message import EmailMessage
from app.core.config import settings
from app.core.redis_config import Redis
from fastapi import HTTPException, status, Response
from jose import jwt
from datetime import datetime, timedelta
import secrets


async def generate_otp() -> str:
    return "".join(secrets.choice("0123456789") for _ in range(6))


def send_email(email_content: dict):
    context = ssl.create_default_context()
    msg = EmailMessage()
    msg["Subject"] = email_content.get("subject")
    msg["From"] = settings.SENDER_EMAIL
    msg["To"] = email_content.get("receiver_email")
    msg.set_content(email_content.get("body"))
    if email_content.get("cc"):
        msg["Cc"] = email_content.get("cc")
    if email_content.get("bcc"):
        msg["Bcc"] = email_content.get("bcc")
    if email_content.get("html_body"):
        msg.add_alternative(email_content.get("html_body"), subtype="html")
    with smtplib.SMTP(settings.SMTP_SERVER, settings.SMTP_PORT) as smtp:
        smtp.ehlo()
        smtp.starttls(context=context)
        smtp.ehlo()
        smtp.login(settings.SENDER_EMAIL, settings.EMAIL_APP_KEY)
        smtp.send_message(msg=msg)


async def validate_otp(email: str, otp: str, redis: Redis) -> bool:
    get_email_from_redis = await redis.hgetall(name=email)

    if get_email_from_redis:
        tries_left = int(get_email_from_redis.get("tries"))
        if get_email_from_redis.get("otp") == otp:
            await redis.delete(email)
            return True
        else:
            new_tries_left = str(tries_left - 1)
            await redis.hsetex(
                name=email, key="tries", value=new_tries_left, keepttl=True
            )
            if new_tries_left == 0:
                await redis.delete(email)
                return HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"All tries exhausted",
                )
            return HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"OTP is incorrect {new_tries_left} tries left",
            )
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="OTP not found")


async def encode_jwt(payload: dict, expire_time: datetime, secret_key: str) -> str:
    token_payload = payload
    token_payload["expires"] = expire_time
    token = jwt.encode(token_payload, secret_key, algorithm=settings.JWT_ALGORITHM)
    return token


async def decode_jwt(token: str, jwt_secret_key: str) -> dict:
    payload = jwt.decode(token, jwt_secret_key, algorithms=[settings.JWT_ALGORITHM])
    if payload.get("expires") < datetime.now():
        return None
    else:
        return payload


async def generate_access_token_and_refresh_token(payload: dict, response: Response):
    access_token = await encode_jwt(
        payload=payload,
        expire_time=str(
            datetime.now() + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
        ),
        secret_key=settings.JWT_SECRET_ACCESS_KEY,
    )

    refresh_token = await encode_jwt(
        payload=payload,
        expire_time=str(
            datetime.now() + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)
        ),
        secret_key=settings.JWT_SECRET_REFRESH_KEY,
    )

    response.set_cookie(key="access_token", value=access_token)
    response.set_cookie(key="refresh_token", value=refresh_token)
