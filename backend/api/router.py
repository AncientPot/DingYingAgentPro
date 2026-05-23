from fastapi import APIRouter
from backend.api.sessions import router as sessions_router
from backend.api.configs import router as configs_router, settings_router
from backend.api.chat import router as chat_router
from backend.api.tools import router as tools_router
from backend.api.models import router as models_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(sessions_router)
api_router.include_router(configs_router)
api_router.include_router(settings_router)
api_router.include_router(chat_router)
api_router.include_router(tools_router)
api_router.include_router(models_router)
