from fastapi import APIRouter
from app.api.v1.auth_routes import auth_router, google_auth_router
from app.api.v1.admin_routes import admin_router
from app.api.v1.theatre_admin_routes import theatre_admin_router
from app.api.v1.search_route import search_router
from app.api.v1.user_routes import user_router

api_v1_router = APIRouter(prefix="/v1")

api_v1_router.include_router(auth_router)
api_v1_router.include_router(google_auth_router)
api_v1_router.include_router(admin_router)
api_v1_router.include_router(theatre_admin_router)
api_v1_router.include_router(search_router)
api_v1_router.include_router(user_router)
