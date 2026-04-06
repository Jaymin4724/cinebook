from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.api.routes import api_router
from app.core.es_config import es, create_index

# Note: Keep the import of search_sync to ensure listeners are registered
from app.services import search_sync


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

app.include_router(api_router)
