import time
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.redis_config import get_redis


class RateLimitingMiddleware(BaseHTTPMiddleware):

    def __init__(self, app, capacity: int, refill_rate: float):
        super().__init__(app)
        self.capacity = capacity
        self.refill_rate = refill_rate

    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host
        key = f"rate_limit:{client_ip}"
        now = time.time()

        redis_client = get_redis()

        data = await redis_client.hgetall(key)

        if not data:
            tokens = float(self.capacity)
            last_refill = now
        else:
            last_tokens = float(data['tokens'])
            last_refill = float(data['last_refill'])
            refilled_tokens = last_tokens + (now - last_refill) * self.refill_rate
            tokens = min(self.capacity, refilled_tokens)
            last_refill = now

        if tokens >= 1:
            await redis_client.hset(key, mapping={"tokens": tokens - 1, "last_refill": last_refill})
            await redis_client.expire(key, int(self.capacity / self.refill_rate) + 60)
            return await call_next(request)
        else:
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "detail": "Too many requests"
                }
            )