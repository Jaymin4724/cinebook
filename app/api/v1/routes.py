from fastapi import APIRouter
from app.api.v1.auth_routes import auth_router, google_auth_router 

api_v1_router = APIRouter(prefix='/v1')

api_v1_router.include_router(auth_router)
api_v1_router.include_router(google_auth_router)