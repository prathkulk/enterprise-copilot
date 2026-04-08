from fastapi import APIRouter

from backend.app.api.routes.chat import router as chat_router
from backend.app.api.routes.collections import router as collections_router
from backend.app.api.routes.documents import router as documents_router
from backend.app.api.routes.jobs import router as jobs_router
from backend.app.api.routes.retrieval import router as retrieval_router
from backend.app.api.routes.system import router as system_router
from backend.app.api.routes.vector_debug import router as vector_debug_router

api_router = APIRouter()
api_router.include_router(system_router)
api_router.include_router(chat_router)
api_router.include_router(collections_router)
api_router.include_router(documents_router)
api_router.include_router(jobs_router)
api_router.include_router(retrieval_router)
api_router.include_router(vector_debug_router)
