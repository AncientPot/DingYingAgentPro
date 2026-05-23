from pydantic import BaseModel


class ToolMetaResponse(BaseModel):
    name: str
    description: str
    source_file: str
    trust_level: str
    is_active: bool


class ToolReloadResponse(BaseModel):
    added: list[str]
    removed: list[str]
    unchanged: list[str]


class ToolToggleRequest(BaseModel):
    is_active: bool


class ModelInfoResponse(BaseModel):
    name: str
    provider: str
    max_tokens: int
