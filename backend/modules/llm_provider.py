from langchain_deepseek import ChatDeepSeek
from backend.config import settings

AVAILABLE_MODELS = [
    {"name": "deepseek-chat", "provider": "deepseek", "max_tokens": 8192},
    {"name": "deepseek-reasoner", "provider": "deepseek", "max_tokens": 65536},
]


class LLMProvider:
    def __init__(self) -> None:
        self._model_cache: dict[str, ChatDeepSeek] = {}

    def get_model(self, model_name: str, temperature: float, max_tokens: int = 4096) -> ChatDeepSeek:
        cache_key = f"{model_name}:{temperature}:{max_tokens}"
        if cache_key not in self._model_cache:
            self._model_cache[cache_key] = ChatDeepSeek(
                model=model_name,
                temperature=temperature,
                max_tokens=max_tokens,
                api_key=settings.deepseek_api_key,
            )
        return self._model_cache[cache_key]

    def list_available_models(self) -> list[dict]:
        return AVAILABLE_MODELS

    def validate_model(self, model_name: str) -> bool:
        return any(m["name"] == model_name for m in AVAILABLE_MODELS)
