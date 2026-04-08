import secrets
from datetime import datetime, timedelta, timezone
from jose import jwt
from fastapi import Response, HTTPException, status
from app.core.config import settings
from app.core.redis_config import Redis


def generate_otp() -> str:
    return "".join(secrets.choice("0123456789") for _ in range(6))


async def validate_otp(email: str, otp: str, redis: Redis) -> bool:
    cached_data = await redis.hgetall(name=email)

    if not cached_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="OTP not found or expired"
        )

    stored_otp = cached_data.get("otp")
    tries_left = int(cached_data.get("tries", 0))

    if stored_otp == otp:
        await redis.delete(email)
        return True

    new_tries = tries_left - 1
    if new_tries <= 0:
        await redis.delete(email)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="All tries exhausted. Please request a new OTP.",
        )

    await redis.hset(name=email, key="tries", value=str(new_tries))
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=f"Incorrect OTP. {new_tries} tries left.",
    )


def _generate_token(
    data: dict, expires_delta: timedelta, secret: str, token_type: str
) -> str:
    to_encode = data.copy()

    if "user_id" in to_encode:
        to_encode["sub"] = str(to_encode.pop("user_id"))
    elif "sub" in to_encode and not isinstance(to_encode["sub"], str):
        to_encode["sub"] = str(to_encode["sub"])

    expire = datetime.now(timezone.utc) + expires_delta
    to_encode.update({"exp": expire, "type": token_type})

    return jwt.encode(to_encode, secret, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str, secret: str) -> dict | None:

    payload = jwt.decode(token, secret)

    if not payload:
        return None

    expire_time = payload.get("exp")
    if expire_time:
        if datetime.fromtimestamp(expire_time, timezone.utc) < datetime.now(
            timezone.utc
        ):
            return None
    return payload


def generate_access_token_and_refresh_token(payload: dict, response: Response):
    access_token = _generate_token(
        data=payload,
        expires_delta=timedelta(minutes=int(settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)),
        secret=settings.JWT_SECRET_ACCESS_KEY,
        token_type="access",
    )

    refresh_token = _generate_token(
        data=payload,
        expires_delta=timedelta(days=int(settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)),
        secret=settings.JWT_SECRET_REFRESH_KEY,
        token_type="refresh",
    )

    response.set_cookie(key="access_token", value=access_token, httponly=True)
    response.set_cookie(key="refresh_token", value=refresh_token, httponly=True)
    return {"access_token": access_token, "refresh_token": refresh_token}