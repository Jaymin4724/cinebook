from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.api.routes import api_router
from app.core.es_config import es, create_index
from app.middlewares import GlobalExceptionHandlerMiddleware, RateLimitingMiddleware

from app.services import search_sync
from app.core.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- Startup ---
    # This ensures the index exists every time the app starts
    await create_index()

    yield  # The app runs here

    # --- Shutdown ---
    await es.close()
    print("Elasticsearch connection closed safely.")


app = FastAPI(lifespan=lifespan)

if not settings.ENV == "TESTING":
    app.add_middleware(RateLimitingMiddleware, capacity=10, refill_rate=0.1)
app.add_middleware(GlobalExceptionHandlerMiddleware)

app.include_router(api_router)
