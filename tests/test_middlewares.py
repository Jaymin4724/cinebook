import httpx
import pytest
from fastapi import FastAPI
from httpx import ASGITransport

from app.middlewares.global_exception_handler_middleware import (
    GlobalExceptionHandlerMiddleware,
)
from app.middlewares.rate_limiting_middleware import RateLimitingMiddleware


# --- GLOBAL EXCEPTION HANDLER ---
@pytest.fixture
def crashing_app():
    app = FastAPI()
    app.add_middleware(GlobalExceptionHandlerMiddleware)

    @app.get("/boom")
    async def boom():
        raise RuntimeError("unexpected explosion")

    @app.get("/fine")
    async def fine():
        return {"ok": True}

    return app


async def test_unhandled_exception_becomes_uniform_500(crashing_app):
    transport = ASGITransport(app=crashing_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        response = await c.get("/boom")

    assert response.status_code == 500
    assert response.json() == {
        "error": "Internal server error",
        "detail": "Internal server error",
    }


async def test_normal_responses_pass_through(crashing_app):
    transport = ASGITransport(app=crashing_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        response = await c.get("/fine")

    assert response.status_code == 200
    assert response.json() == {"ok": True}


# --- RATE LIMITING (TOKEN BUCKET) ---
async def test_rate_limit_blocks_after_capacity(fake_redis, monkeypatch):
    monkeypatch.setattr(
        "app.middlewares.rate_limiting_middleware.get_redis", lambda: fake_redis
    )

    app = FastAPI()
    # tiny refill rate so the bucket does not meaningfully refill mid-test
    app.add_middleware(RateLimitingMiddleware, capacity=2, refill_rate=0.001)

    @app.get("/ping")
    async def ping():
        return {"ok": True}

    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        assert (await c.get("/ping")).status_code == 200
        assert (await c.get("/ping")).status_code == 200

        response = await c.get("/ping")

    assert response.status_code == 429
    assert response.json()["detail"] == "Too many requests"
