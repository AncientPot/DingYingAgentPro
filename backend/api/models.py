from fastapi import APIRouter, Request
from backend.modules.llm_provider import LLMProvider
from backend.schemas.tool import ModelInfoResponse

router = APIRouter(prefix="/models", tags=["models"])


@router.get("", response_model=list[ModelInfoResponse])
async def list_models(request: Request):
    provider: LLMProvider = request.app.state.llm_provider
    return provider.list_available_models()
