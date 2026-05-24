"""Pydantic 请求/响应模型。"""

from pydantic import BaseModel, Field
from typing import Any, Optional


# ── 聊天 ──

class ChatRequest(BaseModel):
    session_name: str = Field(..., description="会话名称，不存在则自动创建")
    message: str = Field(..., min_length=1, description="用户消息内容")


class ChatResponse(BaseModel):
    session_name: str
    role: str = "assistant"
    content: str
    tool_calls: Optional[list[dict]] = None
    tokens: int = 0


# ── 会话 ──

class SessionCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, description="新会话名称")


class SessionInfo(BaseModel):
    name: str
    thread_id: str


class SessionListResponse(BaseModel):
    sessions: list[SessionInfo]


# ── 设置 ──

class ConfigItem(BaseModel):
    key: str = Field(..., description="配置键")
    value: Any = Field(..., description="配置值（原生类型，敏感字段已脱敏）")
    description: str = ""


class ConfigResponse(BaseModel):
    configs: list[ConfigItem]


class ConfigUpdateRequest(BaseModel):
    model_name: Optional[str] = None
    temperature: Optional[float] = None
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    system_prompt: Optional[str] = None
    max_search_results: Optional[int] = None
    enabled_tools: Optional[list[str]] = None


# ── 工具 ──

class ToolInfo(BaseModel):
    name: str = Field(..., description="工具模块文件名")
    display_name: str = Field(..., description="工具显示名称")
    description: str = ""
    enabled: bool = False


class ToolListResponse(BaseModel):
    tools: list[ToolInfo]


class ToolToggleRequest(BaseModel):
    enabled: bool = Field(..., description="是否启用")


# ── 工具测试 ──

class ToolTestResponse(BaseModel):
    ok: bool = Field(..., description="测试是否通过")
    message: str = Field(..., description="测试结果描述")
    details: str = Field("", description="详细诊断信息")


# ── 通用 ──

class MessageResponse(BaseModel):
    detail: str
