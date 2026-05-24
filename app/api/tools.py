"""工具管理接口 —— 供前端工具管理页面调用。"""

import logging

from fastapi import APIRouter, HTTPException

from app.models.schemas import MessageResponse, ToolInfo, ToolListResponse, ToolToggleRequest
from app.services.tool_service import get_tools_status, set_tool_enabled

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/tools", tags=["tools"])


@router.get("", response_model=ToolListResponse)
def list_tools():
    """列出所有可用工具及其启用状态。"""
    tools = get_tools_status()
    return ToolListResponse(tools=[ToolInfo(**t) for t in tools])


@router.put("/{tool_name}", response_model=ToolInfo)
def toggle_tool(tool_name: str, req: ToolToggleRequest):
    """
    启用或禁用指定工具。
    变更后 Agent 图会自动重建以反映工具集变更。
    """
    success = set_tool_enabled(tool_name, req.enabled)
    if not success:
        raise HTTPException(status_code=404, detail=f"工具 '{tool_name}' 不存在。")
    # 返回工具最新状态
    tools = get_tools_status()
    matched = next((t for t in tools if t["name"] == tool_name), None)
    if matched is None:
        raise HTTPException(status_code=500, detail="工具状态查询失败。")
    return ToolInfo(**matched)
