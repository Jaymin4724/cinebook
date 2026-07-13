import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, status
from fastapi.responses import JSONResponse
from sqlalchemy import text
from app.api.routes import api_router
from app.api.dependencies import DBDep, RedisDep
from app.core.es_config import es, create_index
from app.middlewares import GlobalExceptionHandlerMiddleware, RateLimitingMiddleware

from app.core.config import settings

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- Startup ---
    # This ensures the index exists every time the app starts
    await create_index()

    yield  # The app runs here

    # --- Shutdown ---
    await es.close()
    logger.info("Elasticsearch connection closed safely.")


app = FastAPI(
    title="CineBook",
    description="Online Movie Ticket Booking System",
    lifespan=lifespan,
)

if not settings.ENV == "TESTING":
    app.add_middleware(RateLimitingMiddleware, capacity=10, refill_rate=0.1)
app.add_middleware(GlobalExceptionHandlerMiddleware)

app.include_router(api_router)


@app.get("/health", tags=["health"])
async def health_check(db: DBDep, redis: RedisDep):
    """Report liveness plus reachability of Postgres, Redis, and Elasticsearch."""
    checks = {"database": "ok", "redis": "ok", "elasticsearch": "ok"}

    try:
        await db.execute(text("SELECT 1"))
    except Exception:
        checks["database"] = "unavailable"

    try:
        await redis.ping()
    except Exception:
        checks["redis"] = "unavailable"

    try:
        await es.ping()
    except Exception:
        checks["elasticsearch"] = "unavailable"

    healthy = all(value == "ok" for value in checks.values())

    return JSONResponse(
        status_code=status.HTTP_200_OK if healthy else status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"status": "ok" if healthy else "degraded", "checks": checks},
    )
