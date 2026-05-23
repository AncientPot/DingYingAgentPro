from datetime import datetime
from pydantic import BaseModel, Field


class SessionCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)


class SessionResponse(BaseModel):
    id: str
    name: str
    created_at: str
    updated_at: str


class SessionDetailResponse(SessionResponse):
    config: "SessionConfigResponse | None" = None


class SessionConfigResponse(BaseModel):
    session_id: str
    system_prompt: str
    model_name: str
    temperature: float
    max_tokens: int
    enabled_tools: list[str]
    version: int
    created_at: str
    updated_at: str


class SessionConfigUpdate(BaseModel):
    system_prompt: str | None = None
    model_name: str | None = None
    temperature: float | None = None
    max_tokens: int | None = None
    enabled_tools: list[str] | None = None
    version: int


class ChatMessageResponse(BaseModel):
    id: int
    session_id: str
    role: str
    content: str
    tool_name: str | None = None
    token_count: int = 0
    created_at: str
