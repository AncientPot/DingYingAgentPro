from fastapi import Request
import aiosqlite
from backend.modules.session_store import SessionStore
from backend.modules.config_manager import SessionConfigManager, GlobalSettingsManager
from backend.modules.agent_core import AgentCore
from backend.modules.tool_registry import ToolRegistry


async def get_db(request: Request) -> aiosqlite.Connection:
    return request.app.state.db


def get_session_store(request: Request) -> SessionStore:
    return request.app.state.session_store


def get_config_manager(request: Request) -> SessionConfigManager:
    return request.app.state.config_manager


def get_global_settings(request: Request) -> GlobalSettingsManager:
    return request.app.state.global_settings


def get_agent_core(request: Request) -> AgentCore:
    return request.app.state.agent_core


def get_tool_registry(request: Request) -> ToolRegistry:
    return request.app.state.tool_registry
