from fastapi import APIRouter

from backend.app.api.routes.collections import router as collections_router
from backend.app.api.routes.system import router as system_router

api_router = APIRouter()
api_router.include_router(system_router)
api_router.include_router(collections_router)
