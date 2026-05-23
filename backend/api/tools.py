from fastapi import APIRouter, Depends, HTTPException
from backend.modules.tool_registry import ToolRegistry
from backend.modules.agent_core import AgentCore
from backend.dependencies import get_tool_registry, get_agent_core
from backend.schemas.tool import ToolMetaResponse, ToolReloadResponse, ToolToggleRequest

router = APIRouter(prefix="/tools", tags=["tools"])


@router.get("", response_model=list[ToolMetaResponse])
async def list_tools(
    registry: ToolRegistry = Depends(get_tool_registry),
):
    return registry.get_all_metadata()


@router.post("/reload", response_model=ToolReloadResponse)
async def reload_tools(
    registry: ToolRegistry = Depends(get_tool_registry),
    agent: AgentCore = Depends(get_agent_core),
):
    result = registry.reload()
    await agent.rebuild_graph()
    return result


@router.put("/{tool_name}", response_model=ToolMetaResponse)
async def toggle_tool(
    tool_name: str,
    body: ToolToggleRequest,
    registry: ToolRegistry = Depends(get_tool_registry),
    agent: AgentCore = Depends(get_agent_core),
):
    tool = registry.get_tool(tool_name)
    if tool is None:
        raise HTTPException(404, f"Tool '{tool_name}' not found")

    if body.is_active:
        registry.enable_tool(tool_name)
    else:
        registry.disable_tool(tool_name)

    await agent.rebuild_graph()

    all_meta = registry.get_all_metadata()
    for meta in all_meta:
        if meta["name"] == tool_name:
            return meta
    raise HTTPException(404, f"Tool '{tool_name}' not found")
