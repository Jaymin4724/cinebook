from fastapi import APIRouter
from app.api.v1 import auth_router

api_v1_router = APIRouter(prefix='/v1')

api_v1_router.include_router(auth_router)