from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    deepseek_api_key: str = ""
    tavily_api_key: str = ""
    langchain_tracing_v2: str = ""
    langsmith_api_key: str = ""
    database_url: str = "app.db"
    checkpoint_db_url: str = "checkpoints.sqlite"
    tools_scan_path: str = "./custom_tools"
    default_model: str = "deepseek-chat"
    default_temperature: float = 0.7
    default_max_tokens: int = 4096
    default_system_prompt: str = "你是一个AI助手，请尽你所能回答我的问题。"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
